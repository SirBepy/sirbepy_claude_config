"""PreToolUse gate (todo 467): block a session's FIRST `git push` unless
`snippets/auto-commit.md` has been read this session.

Root incident: a long session skipped the once-per-session read of that
file and pushed six commits, twice, unasked - `auto-commit.md`'s scope
sentence ("this covers committing only, pushing is never automatic") would
have prevented it, had it been read. done/101 dropped the same shape of fix
for the memory rubric because zero harm had resulted yet; here harm already
did, so this ships narrow rather than not at all.

Two arms, same file, distinguished by `hook_event_name`:
- PostToolUse on Read, Bash or PowerShell: records a session-scoped marker
  the moment `snippets/auto-commit.md` is read, by path suffix so any
  relative/absolute form of the path matches. A Read-tool call always
  counts; a Bash/PowerShell call counts only when its first command word is
  a known read command (cat, head, tail, sed, less, more, Get-Content, gc)
  AND a later argument resolves to the snippet path - a command that merely
  mentions the path (`git log -- snippets/auto-commit.md`, `echo
  snippets/auto-commit.md`) does not count (todo 1087, widening the
  matcher todo 1005 had flagged as out of this file's reach).
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
    from _hooklib import read_payload, deny, tokenize_command
except Exception as e:
    sys.stderr.write(f"[push-read-gate] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

SESSION_MARKER_DIR = _HOOKS_DIR / ".session-markers"
READ_MARKER_PREFIX = "read-auto-commit-"
PASSED_MARKER_PREFIX = "push-gate-passed-"
AUTO_COMMIT_SUFFIX = ("snippets", "auto-commit.md")

VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
_SAFE_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

# Chain operators split a compound shell command into independent pieces
# (verified byte-identical against other guards' own copies, e.g.
# dev-backend-guard.py, push-gate.py - no shared constant for it in
# _hooklib yet).
CHAIN_SPLIT_RE = re.compile(r"&&|\|\||;|\n|\|")

# Commands whose first argument is a file they actually read. A command
# that only mentions the path as an argument to something else (git log --,
# echo, grep's search target isn't content-read either) never matches here.
SHELL_READ_COMMANDS = {"cat", "head", "tail", "sed", "less", "more", "get-content", "gc"}


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


def _shell_command_name(tok: str) -> str:
    """Last path segment of `tok`, case-folded - strips a `/bin/cat`-style
    prefix the same way a bare `cat` would match."""
    return re.split(r"[\\/]", tok)[-1].lower()


def is_shell_read_of_auto_commit(command: str) -> bool:
    """True if any chain segment of `command` runs a known read command
    (cat, head, tail, sed, less, more, Get-Content, gc) with a later
    argument that resolves to snippets/auto-commit.md. A path that only
    appears as an argument to an unrelated command (`git log --
    snippets/auto-commit.md`, `echo snippets/auto-commit.md`) does not
    count - the command name itself must be a real read."""
    for segment in CHAIN_SPLIT_RE.split(command or ""):
        tokens = tokenize_command(segment)
        if not tokens:
            continue
        if _shell_command_name(tokens[0]) not in SHELL_READ_COMMANDS:
            continue
        if any(_is_auto_commit_snippet(tok) for tok in tokens[1:]):
            return True
    return False


def handle_post_tool_use(payload: dict) -> None:
    session_id = payload.get("session_id") or ""
    if not _safe_session_id(session_id):
        sys.exit(0)
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    if tool_name == "Read":
        read_hit = _is_auto_commit_snippet(tool_input.get("file_path") or "")
    elif tool_name in ("Bash", "PowerShell"):
        read_hit = is_shell_read_of_auto_commit(tool_input.get("command") or "")
    else:
        read_hit = False
    if not read_hit:
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
        "snippets/auto-commit.md has been read this session (todo 467: a "
        "skipped read of this exact file preceded an unasked-for push). Read "
        "it with the Read tool, or actually read it via a shell command "
        "(`cat`, `head`, `sed`, `Get-Content`, ...) - a command that only "
        "mentions the path, like `git log -- snippets/auto-commit.md` or "
        "`echo snippets/auto-commit.md`, does not count. Then retry - every "
        "later push this session is ungated."
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
