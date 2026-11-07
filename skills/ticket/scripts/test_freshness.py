"""Offline tests for freshness.py (pc-1304): real throwaway git repos, a stubbed Shortcut API."""

import io
import contextlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import freshness as fr
import shortcut_triage as st


def git(repo: Path, *args: str) -> str:
    # Inline identity: the CI runner has no global git user configured.
    proc = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", "-C", str(repo), *args],
        check=True, capture_output=True, text=True,
    )
    return proc.stdout.strip()


def commit(repo: Path, name: str, subject: str) -> str:
    target = repo / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(subject, encoding="utf-8")
    git(repo, "add", name)
    git(repo, "commit", "-q", "-m", subject)
    return git(repo, "rev-parse", "HEAD")


class TestRepoLines(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        self.origin = root / "origin"
        self.origin.mkdir()
        git(self.origin, "init", "-q", "-b", "develop")
        self.first = commit(self.origin, "lib/ui/biller_landing/slug_screen.dart", "first")
        self.clone = root / "clone"
        subprocess.run(["git", "clone", "-q", str(self.origin), str(self.clone)], check=True, capture_output=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_fetch_picks_up_a_commit_made_after_the_clone(self):
        newer = commit(self.origin, "lib/other.dart", "merged since")
        lines, ok = fr.repo_lines(str(self.clone), "develop", [])
        self.assertTrue(ok)
        self.assertIn(f"origin/develop = {newer} ", lines[0])
        self.assertTrue(lines[0].endswith("merged since"))
        self.assertNotIn(self.first, lines[0])

    def test_find_lists_real_tracked_paths(self):
        lines, ok = fr.repo_lines(str(self.clone), "develop", ["biller_landing", "nothing_like_this"])
        self.assertTrue(ok)
        self.assertIn("lib/ui/biller_landing/slug_screen.dart", lines[1])
        self.assertTrue(lines[2].endswith("none"))

    def test_missing_branch_and_missing_repo_are_failures_not_crashes(self):
        lines, ok = fr.repo_lines(str(self.clone), "no-such-branch", [])
        self.assertFalse(ok)
        self.assertIn("NOT FOUND", lines[0])
        lines, ok = fr.repo_lines(str(Path(self._tmp.name) / "nowhere"), "develop", [])
        self.assertFalse(ok)
        self.assertIn("FETCH FAILED", lines[0])

    def test_repo_arg_splits_on_the_last_at_sign(self):
        self.assertEqual(fr.split_repo_arg("C:/a@b/repo@develop"), ("C:/a@b/repo", "develop"))
        with self.assertRaises(ValueError):
            fr.split_repo_arg("C:/just/a/path")


def fake_api(method, path, token, body=None, timeout=30):
    if path == "/api/v3/workflows":
        return [{"name": "ENG", "states": [{"id": 500, "name": "To Do"}, {"id": 501, "name": "Complete"}]}]
    if path == "/api/v3/stories/1":
        return {"id": 1, "workflow_state_id": 501, "blocked": False, "updated_at": "2026-11-05T14:30:12Z"}
    raise urllib_error(path)


def urllib_error(path):
    import urllib.error
    return urllib.error.HTTPError(path, 404, "Not Found", {}, io.BytesIO())


class TestStoryLines(unittest.TestCase):
    def test_state_is_named_and_a_404_is_reported(self):
        with mock.patch.object(st, "api_call", fake_api):
            lines, ok = fr.story_lines(["sc-1", "2"], "t")
        self.assertFalse(ok)
        self.assertEqual(lines[0], "- sc-1: Complete, blocked=False, updated 2026-11-05T14:30:12Z")
        self.assertEqual(lines[1], "- sc-2: HTTP 404")


class TestReportAndCli(unittest.TestCase):
    def test_report_starts_with_a_dated_header_and_carries_both_kinds(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "r"
            repo.mkdir()
            git(repo, "init", "-q", "-b", "develop")
            sha = commit(repo, "a.txt", "only")
            clone = Path(tmp) / "c"
            subprocess.run(["git", "clone", "-q", str(repo), str(clone)], check=True, capture_output=True)
            with mock.patch.object(st, "api_call", fake_api):
                report, ok = fr.build_report([f"{clone}@develop"], ["1"], [], token="t")
        self.assertTrue(ok)
        self.assertRegex(report.splitlines()[0], r"^Freshness \(fetched \d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ\):$")
        self.assertIn(sha, report)
        self.assertIn("- sc-1: Complete", report)

    def test_cli_needs_a_target(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            fr.main([])

    def test_cli_exit_one_on_a_failed_line(self):
        out = io.StringIO()
        out.buffer = io.BytesIO()
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(sys, "stdout", out):
            rc = fr.main(["--repo", f"{tmp}/nowhere@develop"])
        self.assertEqual(rc, 1)
        self.assertIn(b"FETCH FAILED", out.buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
