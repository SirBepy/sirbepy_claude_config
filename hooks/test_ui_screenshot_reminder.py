"""Self-test for ui-screenshot-reminder.py (todo 326, global reminder rebuild;
todo 821, mtime-compare predicate replacing the once-per-session marker;
todo 487, transcript-based turn attribution replacing whole-tree `git status`).

Run directly: python hooks/test_ui_screenshot_reminder.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_HOOK_PATH = _HOOKS_DIR / "ui-screenshot-reminder.py"
guard = _testlib.load_module("guard", _HOOK_PATH)

# (path, expect_ui, label)
UNIT_CASES = [
    ("src/components/Button.tsx", True, "extension + segment both match"),
    ("lib/features/foo/ui/widget.dart", True, "lib/**/ui/ Flutter path"),
    ("app/screens/Home.jsx", True, "screens segment"),
    ("src/widgets/Card.vue", True, "widgets segment + .vue ext"),
    ("styles/theme.scss", True, ".scss extension alone"),
    ("lib/app_header.dart", True, ".dart extension alone, no ui segment"),
    ("server/routes/users.py", False, "backend python, no match"),
    ("README.md", False, "docs, no match"),
    (".claude\\hooks\\commit-guard.py", False, "windows-style backslash path, backend"),
    ("lib\\ui\\dialog.dart", True, "windows-style backslash path, ui segment"),
]


def touch(path: Path, at: float) -> None:
    """Create (or update) `path` and pin its mtime to `at`, so ordering
    between UI edits and screenshots is deterministic instead of relying on
    real-time sleeps and filesystem clock granularity.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    os.utime(path, (at, at))


def check_unit(case) -> bool:
    path, expect_ui, label = case
    got = guard.is_ui_path(path)
    ok = got == expect_ui
    print(f"[{'PASS' if ok else 'FAIL'}] unit: {label}: {path!r} -> {got}")
    return ok


def write_transcript(tmpdir: Path, tool_blocks: list, name: str = "transcript.jsonl") -> Path:
    """A transcript with one real user message followed by one tool_use block
    per (tool_name, tool_input) pair, matching em-dash-guard.py's test shape
    so both hooks share one mental model of "this turn".
    """
    entries = [
        {"type": "user", "message": {"content": [{"type": "text", "text": "hi"}]}},
    ]
    for tool_name, tool_input in tool_blocks:
        entries.append({
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": tool_name, "input": tool_input}]},
        })
    path = tmpdir / name
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return path


def run_hook(cwd: str, session_id: str, transcript_path: str | None = None) -> subprocess.CompletedProcess:
    payload = {"session_id": session_id, "cwd": cwd}
    if transcript_path:
        payload["transcript_path"] = transcript_path
    return subprocess.run(
        [sys.executable, str(_HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "README.md").write_text("init\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)


def integration_checks() -> list[str]:
    fails: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="ui-reminder-test-"))
    try:
        repo = tmp / "repo"
        repo.mkdir()
        init_repo(repo)

        # Case 1: this turn's own Write touches a UI file, zero screenshots
        # anywhere -> fires (existing zero-screenshot behaviour, no regress).
        session_a = f"test-{uuid.uuid4()}"
        ui_file_a = repo / "src" / "Button.tsx"
        touch(ui_file_a, time.time())
        transcript_a = write_transcript(repo, [("Write", {"file_path": str(ui_file_a)})])
        proc = run_hook(str(repo), session_a, str(transcript_a))
        fired = '"decision": "block"' in proc.stdout
        ok = fired and proc.returncode == 0
        print(f"[{'PASS' if ok else 'FAIL'}] integration: zero screenshots, UI edit fires -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not ok:
            fails.append("zero screenshots fires")

        # Case 2: UI edit recorded, then a screenshot postdating it, then a
        # SECOND UI edit (same transcript entry, later mtime) postdating the
        # screenshot -> must fire (todo 821's core gap).
        repo_c = tmp / "repo-refire"
        repo_c.mkdir()
        init_repo(repo_c)
        session_c = f"test-{uuid.uuid4()}"
        t0 = time.time()
        ui_file = repo_c / "lib" / "ui" / "widget.dart"
        touch(ui_file, t0)
        transcript_c = write_transcript(repo_c, [("Edit", {"file_path": str(ui_file)})])
        touch(repo_c / ".for_bepy" / "screenshots" / "sess-1" / "shot.png", t0 + 100)
        # Sanity: screenshot already postdates the only edit -> quiet here.
        pre = run_hook(str(repo_c), session_c, str(transcript_c))
        pre_ok = pre.stdout.strip() == "" and pre.returncode == 0
        print(f"[{'PASS' if pre_ok else 'FAIL'}] integration: refire setup, screenshot postdates edit stays quiet -> exit={pre.returncode} stdout={pre.stdout.strip()!r}")
        if not pre_ok:
            fails.append("refire setup quiet before second edit")
        touch(ui_file, t0 + 200)
        proc = run_hook(str(repo_c), session_c, str(transcript_c))
        fired = '"decision": "block"' in proc.stdout
        ok = fired and proc.returncode == 0
        print(f"[{'PASS' if ok else 'FAIL'}] integration: second UI edit after screenshot fires -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not ok:
            fails.append("second UI edit after screenshot fires")

        # Case 3: UI edit, then a screenshot postdating it, no further edit
        # -> stays quiet.
        repo_d = tmp / "repo-covered"
        repo_d.mkdir()
        init_repo(repo_d)
        session_d = f"test-{uuid.uuid4()}"
        t0 = time.time()
        ui_file_d = repo_d / "lib" / "ui" / "widget.dart"
        touch(ui_file_d, t0)
        transcript_d = write_transcript(repo_d, [("Edit", {"file_path": str(ui_file_d)})])
        touch(repo_d / ".for_bepy" / "screenshots" / "sess-1" / "shot.png", t0 + 100)
        proc = run_hook(str(repo_d), session_d, str(transcript_d))
        silent = proc.stdout.strip() == "" and proc.returncode == 0
        print(f"[{'PASS' if silent else 'FAIL'}] integration: screenshot covers last edit, no further edit stays quiet -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not silent:
            fails.append("screenshot covers edit stays quiet")

        # Case 4: this turn's own edit is backend-only -> silent, new session
        # (fresh repo, so case 1's leftover untracked .tsx file can't leak in).
        repo_b = tmp / "repo-backend"
        repo_b.mkdir()
        init_repo(repo_b)
        session_b = f"test-{uuid.uuid4()}"
        backend_file = repo_b / "server" / "app.py"
        touch(backend_file, time.time())
        transcript_b = write_transcript(repo_b, [("Edit", {"file_path": str(backend_file)})])
        proc = run_hook(str(repo_b), session_b, str(transcript_b))
        silent = proc.stdout.strip() == "" and proc.returncode == 0
        print(f"[{'PASS' if silent else 'FAIL'}] integration: backend-only changes stay silent -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not silent:
            fails.append("backend-only silent")

        # Case 5: no transcript at all, no-git-repo cwd -> does not crash,
        # stays silent (no tool_use to attribute anything to).
        non_repo = tmp / "not-a-repo"
        non_repo.mkdir()
        session_e = f"test-{uuid.uuid4()}"
        proc = run_hook(str(non_repo), session_e)
        ok = proc.returncode == 0 and proc.stdout.strip() == ""
        print(f"[{'PASS' if ok else 'FAIL'}] integration: no-git-repo does not crash -> exit={proc.returncode} stdout={proc.stdout.strip()!r} stderr={proc.stderr.strip()!r}")
        if not ok:
            fails.append("no-git-repo does not crash")

        # Case 5b: this turn's own edit lands outside any git repo -> repo
        # root resolution fails, falls back to payload cwd, still fires
        # (proves the fallback path doesn't silently swallow a real edit).
        non_repo2 = tmp / "not-a-repo-2"
        non_repo2.mkdir()
        session_f = f"test-{uuid.uuid4()}"
        ui_file_f = non_repo2 / "src" / "Widget.tsx"
        touch(ui_file_f, time.time())
        transcript_f = write_transcript(non_repo2, [("Write", {"file_path": str(ui_file_f)})])
        proc = run_hook(str(non_repo2), session_f, str(transcript_f))
        fired = '"decision": "block"' in proc.stdout
        ok = fired and proc.returncode == 0
        print(f"[{'PASS' if ok else 'FAIL'}] integration: non-repo UI edit still fires via cwd fallback -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not ok:
            fails.append("non-repo edit fires via fallback")

        # Case 6: malformed stdin (forces an internal exception) -> exits 0.
        proc = subprocess.run(
            [sys.executable, str(_HOOK_PATH)],
            input="not valid json {{{",
            capture_output=True,
            text=True,
        )
        ok = proc.returncode == 0
        print(f"[{'PASS' if ok else 'FAIL'}] integration: thrown internal error still exits 0 -> exit={proc.returncode} stderr={proc.stderr.strip()!r}")
        if not ok:
            fails.append("thrown internal error exits 0")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return fails


def run_487_regression() -> list[str]:
    """Todo 487's reported shape: a UI file already dirty in the tree BEFORE
    the turn started (never mentioned in the transcript) must not fire, even
    while this same turn touches an unrelated file. A UI file this turn's
    own tool calls DID touch must still fire, dirt or no dirt.
    """
    fails: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="ui-reminder-487-"))
    try:
        repo = tmp / "repo"
        repo.mkdir()
        init_repo(repo)
        session = f"test-{uuid.uuid4()}"

        # Pre-existing dirt: a peer session's (or an earlier turn's) leftover
        # uncommitted UI file, on disk but absent from this turn's transcript.
        dirty_css = repo / "src" / "already-dirty.css"
        touch(dirty_css, time.time())

        # This turn's own edit is a plain markdown file.
        md_file = repo / "NOTES.md"
        touch(md_file, time.time())
        transcript = write_transcript(repo, [("Write", {"file_path": str(md_file)})])
        proc = run_hook(str(repo), session, str(transcript))
        silent = proc.stdout.strip() == "" and proc.returncode == 0
        print(f"[{'PASS' if silent else 'FAIL'}] regression 487: pre-existing dirty .css ignored, turn only touched .md -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not silent:
            fails.append("487: pre-existing dirt ignored")

        # Same repo, same dirt still on disk - but this turn ALSO edits a
        # real UI file -> must still fire.
        ui_file = repo / "src" / "Widget.tsx"
        touch(ui_file, time.time())
        transcript2 = write_transcript(
            repo,
            [("Write", {"file_path": str(md_file)}), ("Edit", {"file_path": str(ui_file)})],
            name="transcript2.jsonl",
        )
        proc2 = run_hook(str(repo), session, str(transcript2))
        fired = '"decision": "block"' in proc2.stdout
        ok = fired and proc2.returncode == 0
        print(f"[{'PASS' if ok else 'FAIL'}] regression 487: this turn's own UI edit still fires despite pre-existing dirt -> exit={proc2.returncode} stdout={proc2.stdout.strip()!r}")
        if not ok:
            fails.append("487: turn's own UI edit still fires")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return fails


def run_readonly_regression() -> list[str]:
    """A read-only turn (Grep/Read only, zero Edit/Write/MultiEdit/
    NotebookEdit calls) must never fire, however dirty the tree - even when
    the only tool call reads the exact UI file that is dirty (from 825)."""
    fails: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="ui-reminder-ro-"))
    try:
        repo = tmp / "repo"
        repo.mkdir()
        init_repo(repo)
        session = f"test-{uuid.uuid4()}"
        dirty_ui = repo / "lib" / "ui" / "widget.dart"
        touch(dirty_ui, time.time())
        transcript = write_transcript(repo, [
            ("Grep", {"pattern": "foo"}),
            ("Read", {"file_path": str(dirty_ui)}),
        ])
        proc = run_hook(str(repo), session, str(transcript))
        silent = proc.stdout.strip() == "" and proc.returncode == 0
        print(f"[{'PASS' if silent else 'FAIL'}] regression 487: read-only turn never fires, even reading the dirty UI file -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not silent:
            fails.append("487: read-only turn stays silent")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return fails


def run_cwd_drift_regression() -> list[str]:
    """Todo 487: a turn's edit in repo A must be judged against repo A even
    when payload["cwd"] drifted to repo B (a later Bash command's cd), and
    repo B's own screenshots must not suppress repo A's reminder.
    """
    fails: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="ui-reminder-cwd-"))
    try:
        repo_a = tmp / "repo-a"
        repo_a.mkdir()
        init_repo(repo_a)
        repo_b = tmp / "repo-b"
        repo_b.mkdir()
        init_repo(repo_b)
        session = f"test-{uuid.uuid4()}"

        ui_file = repo_a / "src" / "Widget.tsx"
        touch(ui_file, time.time())
        transcript = write_transcript(repo_a, [("Edit", {"file_path": str(ui_file)})])

        # payload cwd points at repo B (drifted); the transcript's edit is in repo A.
        proc = run_hook(str(repo_b), session, str(transcript))
        fired = '"decision": "block"' in proc.stdout
        ok = fired and proc.returncode == 0
        print(f"[{'PASS' if ok else 'FAIL'}] regression 487: repo A edit fires though payload cwd drifted to repo B -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not ok:
            fails.append("487: fires despite drifted cwd")

        # repo B has its own unrelated screenshot; it must not suppress repo
        # A's reminder (proves the screenshot scan is repo-scoped, not cwd-scoped).
        touch(repo_b / ".for_bepy" / "screenshots" / "s" / "shot.png", time.time() + 500)
        proc2 = run_hook(str(repo_b), session, str(transcript))
        fired2 = '"decision": "block"' in proc2.stdout
        ok2 = fired2 and proc2.returncode == 0
        print(f"[{'PASS' if ok2 else 'FAIL'}] regression 487: repo B's screenshot does not suppress repo A's reminder -> exit={proc2.returncode} stdout={proc2.stdout.strip()!r}")
        if not ok2:
            fails.append("487: repo B screenshot wrongly suppresses repo A")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return fails


def run() -> int:
    fails = (
        _testlib.run_cases(UNIT_CASES, check_unit)
        + integration_checks()
        + run_487_regression()
        + run_readonly_regression()
        + run_cwd_drift_regression()
    )
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
