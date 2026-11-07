#!/usr/bin/env python3
"""Self-contained test for check-ran.py: builds a throwaway skill folder, never reads the real .runs/.

Run: python test_check_ran.py
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "check-ran.py"


def run(skill: Path, args=(), date=None, cwd=None):
    env = {k: v for k, v in os.environ.items() if k != "CC_SCHEDULE_DATE"}
    env["CLOCKIFY_SKILL_DIR"] = str(skill)
    if date is not None:
        env["CC_SCHEDULE_DATE"] = date
    return subprocess.run([sys.executable, str(SCRIPT), *args], env=env, cwd=cwd,
                          capture_output=True, text=True, timeout=30)


class CheckRan(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.skill = Path(self._tmp.name) / "skill"
        self.repo = Path(self._tmp.name) / "work" / "app"
        (self.skill / "projects").mkdir(parents=True)
        self.repo.mkdir(parents=True)
        (self.skill / "projects" / "demo.md").write_text(
            f"clockify_workspace_id: w\nrepos:\n  - {self.repo.as_posix()}  # main\n  - /nowhere/else\nticket_regex: x\n",
            encoding="utf-8")
        self.addCleanup(self._tmp.cleanup)

    def mark(self, project, date, body="started LOCAL 23:55, window yesterday"):
        d = self.skill / ".runs" / project
        d.mkdir(parents=True, exist_ok=True)
        (d / date).write_text(body, encoding="utf-8")

    def test_marker_present_exits_0_with_reason(self):
        self.mark("demo", "2026-11-05")
        r = run(self.skill, ["demo"], date="2026-11-05")
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "already ran for 2026-11-05"))

    def test_marker_absent_exits_1_silently(self):
        self.mark("demo", "2026-11-04")
        r = run(self.skill, ["demo"], date="2026-11-05")
        self.assertEqual((r.returncode, r.stdout, r.stderr), (1, "", ""))

    def test_no_runs_dir_exits_1(self):
        self.assertEqual(run(self.skill, ["demo"], date="2026-11-05").returncode, 1)

    def test_other_projects_marker_does_not_count(self):
        self.mark("other", "2026-11-05")
        self.assertEqual(run(self.skill, ["demo"], date="2026-11-05").returncode, 1)

    def test_project_resolved_from_cwd(self):
        self.mark("demo", "2026-11-05")
        sub = self.repo / "src"
        sub.mkdir()
        self.assertEqual(run(self.skill, [], date="2026-11-05", cwd=self.repo).returncode, 0)
        self.assertEqual(run(self.skill, [], date="2026-11-05", cwd=sub).returncode, 0)

    def test_unmatched_cwd_fails_open(self):
        self.mark("demo", "2026-11-05")
        self.assertEqual(run(self.skill, [], date="2026-11-05", cwd=self._tmp.name).returncode, 1)

    def test_sibling_folder_with_shared_prefix_is_not_the_repo(self):
        self.mark("demo", "2026-11-05")
        sib = self.repo.parent / "app-extra"
        sib.mkdir()
        self.assertEqual(run(self.skill, [], date="2026-11-05", cwd=sib).returncode, 1)

    def test_cwd_matching_two_configs_fails_open(self):
        (self.skill / "projects" / "dup.md").write_text(f"repos:\n  - {self.repo.as_posix()}\n", encoding="utf-8")
        self.mark("demo", "2026-11-05")
        self.mark("dup", "2026-11-05")
        self.assertEqual(run(self.skill, [], date="2026-11-05", cwd=self.repo).returncode, 1)

    def test_bad_date_or_name_fails_open(self):
        # Markers sit at the exact paths an unvalidated traversal would resolve to, so dropping the
        # date/name validation turns these into exit 0.
        self.mark("demo", "2026-11-05")
        (self.skill / ".runs" / "2026-11-05").write_text("x", encoding="utf-8")
        (self.skill / "demo").mkdir()
        (self.skill / "demo" / "2026-11-05").write_text("x", encoding="utf-8")
        self.assertEqual(run(self.skill, ["demo"], date="../2026-11-05").returncode, 1)
        self.assertEqual(run(self.skill, ["../demo"], date="2026-11-05").returncode, 1)

    def test_marker_directory_is_not_a_marker(self):
        (self.skill / ".runs" / "demo" / "2026-11-05").mkdir(parents=True)
        self.assertEqual(run(self.skill, ["demo"], date="2026-11-05").returncode, 1)

    def test_default_date_is_today_when_env_unset(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("check_ran", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.mark("demo", mod.today())
        r = run(self.skill, ["demo"])
        self.assertEqual((r.returncode, r.stdout.strip()), (0, f"already ran for {mod.today()}"))

    def test_firing_just_after_midnight_belongs_to_the_previous_day(self):
        import datetime
        import importlib.util
        spec = importlib.util.spec_from_file_location("check_ran", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        d = datetime.datetime
        self.assertEqual(mod.day_for(d(2026, 11, 8, 0, 3)), "2026-11-07")
        self.assertEqual(mod.day_for(d(2026, 11, 8, 5, 59)), "2026-11-07")
        self.assertEqual(mod.day_for(d(2026, 11, 8, 6, 0)), "2026-11-08")
        self.assertEqual(mod.day_for(d(2026, 11, 7, 23, 55)), "2026-11-07")


if __name__ == "__main__":
    unittest.main()
