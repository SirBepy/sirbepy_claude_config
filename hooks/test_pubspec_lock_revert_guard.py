"""Self-test for pubspec-lock-revert-guard.py.

Run directly: python hooks/test_pubspec_lock_revert_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Drives guard.main() twice per case (PreToolUse then PostToolUse) against a
throwaway `git init` repo with a committed pubspec.lock, MARKER_DIR patched
to a per-test tempdir so runs never collide with a real session's markers.
"""

import contextlib
import io
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "pubspec-lock-revert-guard.py"
)

fails = []


def make_repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=repo, check=True)
    (repo / "pubspec.yaml").write_text("name: x\n", encoding="utf-8")
    (repo / "pubspec.lock").write_text("packages:\n  meta: 1.0.0\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)
    return repo


def fire(event: str, command: str, cwd: str, session_id: str = "s1"):
    guard.read_payload = lambda: {
        "hook_event_name": event,
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": cwd,
        "session_id": session_id,
    }
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            guard.main()
            code = 0
        except SystemExit as e:
            code = e.code
    return code, buf.getvalue()


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir / "markers"
    repo = make_repo(tmpdir)

    # --- sole newly-dirty pubspec.lock: reverted ---
    fire("PreToolUse", "fvm flutter analyze", str(repo))
    (repo / "pubspec.lock").write_text("packages:\n  meta: 1.1.0\n", encoding="utf-8")
    code, out = fire("PostToolUse", "fvm flutter analyze", str(repo))
    reverted = (repo / "pubspec.lock").read_text(encoding="utf-8")
    ok = code == 0 and "Reverted" in out and "1.0.0" in reverted
    fails += [] if ok else ["sole newly-dirty pubspec.lock is reverted"]

    # --- genuine dependency change: pubspec.yaml also newly dirty, left alone ---
    fire("PreToolUse", "flutter run", str(repo))
    (repo / "pubspec.yaml").write_text("name: x\ndependencies:\n  foo: 1.0.0\n", encoding="utf-8")
    (repo / "pubspec.lock").write_text("packages:\n  foo: 1.0.0\n", encoding="utf-8")
    code, out = fire("PostToolUse", "flutter run", str(repo))
    lock_after = (repo / "pubspec.lock").read_text(encoding="utf-8")
    ok = out == "" and "foo: 1.0.0" in lock_after
    fails += [] if ok else ["pubspec.yaml also dirty leaves pubspec.lock untouched"]
    subprocess.run(["git", "checkout", "--", "pubspec.yaml", "pubspec.lock"], cwd=repo, check=True)

    # --- lock already dirty before the command: left alone ---
    (repo / "pubspec.lock").write_text("packages:\n  meta: 9.9.9\n", encoding="utf-8")
    fire("PreToolUse", "fvm flutter analyze", str(repo))
    code, out = fire("PostToolUse", "fvm flutter analyze", str(repo))
    lock_after = (repo / "pubspec.lock").read_text(encoding="utf-8")
    ok = out == "" and "9.9.9" in lock_after
    fails += [] if ok else ["pre-existing dirty pubspec.lock is left alone"]
    subprocess.run(["git", "checkout", "--", "pubspec.lock"], cwd=repo, check=True)

    # --- non-matching command: no marker written, no action ---
    fire("PreToolUse", "flutter test", str(repo))
    (repo / "pubspec.lock").write_text("packages:\n  meta: 2.0.0\n", encoding="utf-8")
    code, out = fire("PostToolUse", "flutter test", str(repo))
    lock_after = (repo / "pubspec.lock").read_text(encoding="utf-8")
    ok = out == "" and "2.0.0" in lock_after
    fails += [] if ok else ["non-matching command never fires"]
    subprocess.run(["git", "checkout", "--", "pubspec.lock"], cwd=repo, check=True)

    # --- no baseline marker (Post with no prior Pre): no action ---
    (repo / "pubspec.lock").write_text("packages:\n  meta: 3.0.0\n", encoding="utf-8")
    code, out = fire("PostToolUse", "fvm flutter analyze", str(repo), session_id="s-no-pre")
    lock_after = (repo / "pubspec.lock").read_text(encoding="utf-8")
    ok = out == "" and "3.0.0" in lock_after
    fails += [] if ok else ["missing baseline marker means no revert"]
    subprocess.run(["git", "checkout", "--", "pubspec.lock"], cwd=repo, check=True)

sys.exit(_testlib.summarize(fails))
