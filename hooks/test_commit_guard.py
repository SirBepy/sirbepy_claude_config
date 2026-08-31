"""Self-test for commit-guard.py.

Run directly: python hooks/test_commit_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Covers is_git_commit_invocation's token-aware detection, then drives the
real guard.main() with a monkeypatched read_payload against a temp
MARKER_DIR/SESSION_MARKER_DIR - no subprocess, no live git, no network.
Per done/335's notes, marker-consume logic itself lives in
_hooklib.consume_fresh_marker and is exercised through the guard's own
constants (MARKER_GLOB, exclude_prefix) rather than re-testing _hooklib
directly. Deny-path assertions check only the exit code (2), never the
reworded bypass message (todo 463), so this suite stays decoupled from
prose.
"""

import os
import sys
import tempfile
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "commit-guard.py"
)

# --- is_git_commit_invocation: token-aware, not a string search ---

INVOCATION_CASES = [
    ("git commit -m 'fix'", True, "plain git commit"),
    ("git commit-graph write", False, "commit-graph is not commit"),
    ("git -C C:/repo commit -m 'x'", True, "git -C <path> commit, value flag skipped"),
    ("git commit --message 'a big commit here'", True, "commit text inside message is fine"),
    ("echo \"git commit\"", False, "git commit only inside a quoted string, one token"),
    ("npm run build && git commit -m 'x'", True, "chained after an unrelated command"),
    ("git status", False, "unrelated git subcommand"),
    ("git --grep=\"commit\" log", False, "commit only inside a flag value"),
]


def check_invocation(case) -> bool:
    command, expected, label = case
    got = guard.is_git_commit_invocation(command)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails = _testlib.run_cases(INVOCATION_CASES, check_invocation)

# --- main() end to end, temp marker dirs only ---


def run_main(command: str, session_id: str = "") -> int:
    guard.read_payload = lambda: {"tool_input": {"command": command}, "session_id": session_id}
    try:
        guard.main()
        return 0
    except SystemExit as e:
        return e.code


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir
    guard.SESSION_MARKER_DIR = tmpdir / ".session-markers"
    guard.SESSION_MARKER_DIR.mkdir(parents=True)

    label = "raw git commit with no marker at all is blocked"
    got = run_main("git commit -m 'x'", session_id="sess-1")
    if not _testlib.report(got == 2, f"{label} (got exit={got})"):
        fails.append(label)

    label = "a non-commit command needs no marker"
    got = run_main("git status", session_id="sess-1")
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)

    # Legacy per-commit marker: consumed on use.
    legacy_marker = tmpdir / ".commit-marker-abc123"
    legacy_marker.touch()
    label = "a fresh legacy .commit-marker is consumed and allows"
    got = run_main("git commit -m 'x'", session_id="sess-2")
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)
    label = "the legacy marker is deleted after being consumed"
    if not _testlib.report(not legacy_marker.exists(), label):
        fails.append(label)
    label = "the same session's next raw commit is blocked again, marker gone"
    got = run_main("git commit -m 'y'", session_id="sess-2")
    if not _testlib.report(got == 2, f"{label} (got exit={got})"):
        fails.append(label)

    # Session marker: never consumed, checked by exact session id.
    session_id = "sess-3"
    session_marker = guard.session_marker_path(session_id)
    session_marker.touch()
    label = "a session marker allows a commit for its exact session id"
    got = run_main("git commit -m 'x'", session_id=session_id)
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)
    label = "the session marker is NOT consumed, unlike the legacy one"
    if not _testlib.report(session_marker.exists(), label):
        fails.append(label)
    label = "a different session id does not see another session's marker"
    got = run_main("git commit -m 'x'", session_id="sess-4")
    if not _testlib.report(got == 2, f"{label} (got exit={got})"):
        fails.append(label)

    # Legacy session marker fallback (pre todo-341 split location).
    legacy_session_id = "sess-5"
    legacy_session_marker = guard.legacy_session_marker_path(legacy_session_id)
    legacy_session_marker.touch()
    label = "a legacy-location session marker still allows its exact session"
    got = run_main("git commit -m 'x'", session_id=legacy_session_id)
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)

    # The legacy session marker's own filename must never satisfy the
    # legacy per-commit glob (exclude_prefix), or a live session marker
    # could be silently eaten by a stray raw commit from another session.
    label = "consume_fresh_marker excludes the legacy session-marker prefix"
    excluded = guard.consume_fresh_marker(
        tmpdir,
        guard.MARKER_GLOB,
        guard.FRESHNESS_SECONDS,
        exclude_prefix=guard.LEGACY_SESSION_MARKER_PREFIX,
    )
    if not _testlib.report(excluded is False, label):
        fails.append(label)

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir
    guard.SESSION_MARKER_DIR = tmpdir / ".session-markers"
    guard.SESSION_MARKER_DIR.mkdir(parents=True)

    saved_bypass = os.environ.pop(guard.OVERRIDE_ENV, None)
    os.environ[guard.OVERRIDE_ENV] = "1"
    try:
        label = "bypass env var allows a raw commit with no marker at all"
        got = run_main("git commit -m 'x'", session_id="sess-6")
        if not _testlib.report(got == 0, f"{label} (got exit={got})"):
            fails.append(label)
    finally:
        os.environ.pop(guard.OVERRIDE_ENV, None)
        if saved_bypass is not None:
            os.environ[guard.OVERRIDE_ENV] = saved_bypass

sys.exit(_testlib.summarize(fails, style="count"))
