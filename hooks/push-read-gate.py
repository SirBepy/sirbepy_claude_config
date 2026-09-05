"""PreToolUse gate (todo 467): block a session's FIRST `git push` unless
`snippets/auto-commit.md` has been read this session.

Root incident: a long session skipped the once-per-session read of that
file and pushed six commits, twice, unasked - `auto-commit.md`'s scope
sentence ("this covers committing only, pushing is never automatic") would
have prevented it, had it been read. done/101 dropped the same shape of fix
for the memory rubric because zero harm had resulted yet; here harm already
did, so this ships narrow rather than not at all.

Two arms, same file, distinguished by `hook_event_name`:
- PostToolUse on Read: records a session-scoped marker the moment
  `snippets/auto-commit.md` is read, by path suffix so any relative/absolute
  form of the path matches.
- PreToolUse on Bash/PowerShell: token-aware `git push` detection (mirrors
  commit-guard.py's `git commit` detection, subcommand renamed). No read
  marker and no prior pass this session -> deny. Once a push is allowed, a
  second marker is written so every later push in the session is unguarded -
  this is a FIRST-push gate only, never a per-push one.

Fails open on any hook error, same philosophy as every other guard here: a
bug in this file must never permanently block git push in every session.
"""

import re
import shlex
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny
except Exception as e:
    sys.stderr.write(f"[push-read-gate] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

SESSION_MARKER_DIR = _HOOKS_DIR / ".session-markers"
READ_MARKER_PREFIX = "read-auto-commit-"
PASSED_MARKER_PREFIX = "push-gate-passed-"
AUTO_COMMIT_SUFFIX = ("snippets", "auto-commit.md")

VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
_SAFE_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _tokenize(command: str) -> list | None:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        return None


def is_git_push_invocation(command: str) -> bool:
    """True if `command` contains a real `git push` subcommand call, walking
    past global flags the same way commit-guard.py does for `git commit`."""
    tokens = _tokenize(command)
    if tokens is None:
        return False
    for i, tok in enumerate(tokens):
        if tok != "git":
            continue
        j = i + 1
        while j < len(tokens) and tokens[j].startswith("-"):
            if tokens[j] in VALUE_FLAGS and "=" not in tokens[j]:
                j += 2
            else:
                j += 1
        if j < len(tokens) and tokens[j] == "push":
            return True
    return False


def _safe_session_id(session_id: str) -> bool:
    return bool(session_id) and bool(_SAFE_SESSION_ID_RE.match(session_id))


def _marker_path(prefix: str, session_id: str) -> Path:
    return SESSION_MARKER_DIR / f"{prefix}{session_id}"


def _is_auto_commit_snippet(file_path: str) -> bool:
    parts = tuple(p.lower() for p in re.split(r"[\\/]", file_path or "") if p)
    return parts[-2:] == AUTO_COMMIT_SUFFIX


def handle_post_tool_use(payload: dict) -> None:
    session_id = payload.get("session_id") or ""
    if not _safe_session_id(session_id):
        sys.exit(0)
    file_path = (payload.get("tool_input") or {}).get("file_path") or ""
    if not _is_auto_commit_snippet(file_path):
        sys.exit(0)
    try:
        SESSION_MARKER_DIR.mkdir(parents=True, exist_ok=True)
        _marker_path(READ_MARKER_PREFIX, session_id).write_text("x", encoding="utf-8")
    except OSError:
        pass
    sys.exit(0)


def handle_pre_tool_use(payload: dict) -> None:
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not is_git_push_invocation(command):
        sys.exit(0)

    session_id = payload.get("session_id") or ""
    if not _safe_session_id(session_id):
        sys.exit(0)  # can't track this session at all, fail open rather than block forever

    if _marker_path(PASSED_MARKER_PREFIX, session_id).exists():
        sys.exit(0)  # not the first push this session, ungated

    if _marker_path(READ_MARKER_PREFIX, session_id).exists():
        try:
            SESSION_MARKER_DIR.mkdir(parents=True, exist_ok=True)
            _marker_path(PASSED_MARKER_PREFIX, session_id).write_text("x", encoding="utf-8")
        except OSError:
            pass
        sys.exit(0)

    deny(
        "[push-read-gate] This session's first `git push` is blocked until "
        "snippets/auto-commit.md has been read this session (todo 467: a skipped "
        "read of this exact file preceded an unasked-for push). Read it, then "
        "retry - every later push this session is ungated."
    )


def main() -> None:
    payload = read_payload()
    if payload.get("hook_event_name") == "PostToolUse":
        handle_post_tool_use(payload)
        return
    handle_pre_tool_use(payload)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[push-read-gate] hook error, failing open: {e}\n")
        sys.exit(0)
