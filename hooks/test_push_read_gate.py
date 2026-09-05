"""Self-test for push-read-gate.py (todo 467).

Run directly: python hooks/test_push_read_gate.py
Drives guard.main() end to end via subprocess against a temp
SESSION_MARKER_DIR, so the on-disk marker behaviour is exercised for real.
"""

import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "push-read-gate.py"
guard = _testlib.load_module("push_read_gate", _GUARD_PATH)

fails = []

# --- is_git_push_invocation: token-aware, mirrors commit-guard's own suite ---

INVOCATION_CASES = [
    ("git push", True, "plain git push"),
    ("git push origin main", True, "push with args"),
    ("git push --force", True, "push with a flag"),
    ("git -C C:/repo push", True, "git -C <path> push, value flag skipped"),
    ("git status", False, "unrelated git subcommand"),
    ("echo \"git push\"", False, "git push only inside a quoted string, one token"),
    ("npm run build && git push", True, "chained after an unrelated command"),
    ("git pushnbump", False, "pushnbump is not push"),
    ("git --grep=\"push\" log", False, "push only inside a flag value"),
]


def check_invocation(case) -> bool:
    command, expected, label = case
    got = guard.is_git_push_invocation(command)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(INVOCATION_CASES, check_invocation)

# --- _is_auto_commit_snippet: path-suffix match, any separator/relative form ---

SNIPPET_PATH_CASES = [
    ("C:/Users/tecno/.claude/snippets/auto-commit.md", True, "absolute forward-slash"),
    (r"C:\Users\tecno\.claude\snippets\auto-commit.md", True, "absolute backslash"),
    ("snippets/auto-commit.md", True, "relative"),
    ("SNIPPETS/AUTO-COMMIT.MD", True, "case-insensitive"),
    ("snippets/terse-replies.md", False, "different snippet file"),
    ("refs/auto-commit.md", False, "same filename, wrong directory"),
    ("", False, "empty path"),
]


def check_snippet_path(case) -> bool:
    path, expected, label = case
    got = guard._is_auto_commit_snippet(path)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(SNIPPET_PATH_CASES, check_snippet_path)

# --- end to end: PostToolUse read marks the session, PreToolUse push checks it ---
# In-process (not subprocess) so the temp SESSION_MARKER_DIR monkeypatch below
# actually reaches guard.main() - a subprocess would re-import the module and
# see the real hooks/.session-markers/ instead.


def call_main(payload: dict) -> int:
    guard.read_payload = lambda: payload
    try:
        guard.main()
        return 0
    except SystemExit as e:
        return e.code


def run_post_read(file_path: str, session_id: str) -> int:
    return call_main({"hook_event_name": "PostToolUse", "tool_name": "Read", "tool_input": {"file_path": file_path}, "session_id": session_id})


def run_pre_push(command: str, session_id: str) -> int:
    return call_main({"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}, "session_id": session_id})


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.SESSION_MARKER_DIR = tmpdir / ".session-markers"

    label = "first push with no read at all is blocked"
    code = run_pre_push("git push", "sess-1")
    ok = code == 2
    fails += [] if _testlib.report(ok, f"{label} (exit={code})") else [label]

    label = "a non-push git command needs no read"
    code = run_pre_push("git status", "sess-1")
    ok = code == 0
    fails += [] if _testlib.report(ok, f"{label} (exit={code})") else [label]

    label = "reading a DIFFERENT file does not satisfy the gate"
    run_post_read("snippets/terse-replies.md", "sess-2")
    code = run_pre_push("git push", "sess-2")
    ok = code == 2
    fails += [] if _testlib.report(ok, f"{label} (exit={code})") else [label]

    label = "reading auto-commit.md then pushing is allowed"
    run_post_read("C:/Users/tecno/.claude/snippets/auto-commit.md", "sess-3")
    code = run_pre_push("git push", "sess-3")
    ok = code == 0
    fails += [] if _testlib.report(ok, f"{label} (exit={code})") else [label]

    label = "a second push the same session is ungated even with the read marker gone"
    guard._marker_path(guard.READ_MARKER_PREFIX, "sess-3").unlink()
    code = run_pre_push("git push origin main", "sess-3")
    ok = code == 0
    fails += [] if _testlib.report(ok, f"{label} (exit={code})") else [label]

    label = "a DIFFERENT session with no read of its own is still blocked"
    code = run_pre_push("git push", "sess-4")
    ok = code == 2
    fails += [] if _testlib.report(ok, f"{label} (exit={code})") else [label]

    label = "a malformed session id fails open rather than blocking forever"
    code = run_pre_push("git push", "$CLAUDE_CODE_SESSION_ID")
    ok = code == 0
    fails += [] if _testlib.report(ok, f"{label} (exit={code})") else [label]

sys.exit(_testlib.summarize(fails, style="count"))
