"""PreToolUse hook: block raw `git commit` outside the /commit skill flow.

Fires on every Bash/PowerShell call. Detects a `git commit` subcommand via
token-aware parsing (not string search) so it can't be fooled by "commit" in
a message/path or tripped by `commit-graph`.

Two marker styles are honoured:
- Session marker (`.session-markers/<session_id>`): written ONCE per
  session, never consumed, matched by exact session id from the hook
  payload - this is what `/commit` writes now, so only the first commit of a
  session pays for the marker-write call. Lives in its own subdirectory, out
  of the glob-matched `.commit-marker*` space, so an external cleanup that
  globs temp per-commit markers can never reach a live session's marker
  (todo 341, 2026-08-16). `legacy_session_marker_path()` is a read-only
  fallback to the pre-split location for markers written before this change.
- Legacy per-commit marker (`.commit-marker-<suffix>` or plain
  `.commit-marker`): fresh-window + oldest-consumed, kept for callers that
  still write one marker per commit (e.g. `/mega-todos` builder agents).

Fails open on any hook error so a bug here can never permanently wedge every
commit in every repo.

Override: set CLAUDE_COMMIT_HOOK_BYPASS=1 in this session's environment
(settings.json "env", or exported before launching claude) to bypass if
/commit is broken - an inline prefix on the command itself does not reach
this hook.
"""

import os
import shlex
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, consume_fresh_marker, FRESHNESS_SECONDS
except Exception as e:
    sys.stderr.write(f"[commit-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

MARKER_DIR = _HOOKS_DIR
MARKER_GLOB = ".commit-marker*"
SESSION_MARKER_DIR = _HOOKS_DIR / ".session-markers"
LEGACY_SESSION_MARKER_PREFIX = ".commit-marker-session-"
OVERRIDE_ENV = "CLAUDE_COMMIT_HOOK_BYPASS"
# Must be set in this session's environment (settings.json "env", or exported
# before launching claude); an inline `VAR=1 <cmd>` prefix never reaches this
# hook, since PreToolUse reads the command string before any shell parses it.

# Short flags that consume a separate following token as their value (so it
# doesn't get mistaken for the subcommand), e.g. `git -C <path> commit ...`.
VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def is_git_commit_invocation(command: str) -> bool:
    """True if `command` contains a real `git commit` subcommand call.

    Token-based: walks past global flags (skipping their values for flags
    like -C) to find the actual subcommand word, so `commit-graph`,
    `--grep="commit"`, or a path/message containing "commit" never match.
    """
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        # Unbalanced quotes etc. - can't safely tokenize; don't block on a guess.
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
        if j < len(tokens) and tokens[j] == "commit":
            return True
    return False


def session_marker_path(session_id: str) -> Path:
    return SESSION_MARKER_DIR / session_id


def legacy_session_marker_path(session_id: str) -> Path:
    """Pre-split location - read-only fallback for a marker written before
    the `.session-markers/` move (todo 341)."""
    return MARKER_DIR / f"{LEGACY_SESSION_MARKER_PREFIX}{session_id}"


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""

    if not is_git_commit_invocation(command):
        sys.exit(0)

    if os.environ.get(OVERRIDE_ENV):
        sys.exit(0)

    session_id = payload.get("session_id") or ""
    if session_id and (
        session_marker_path(session_id).exists()
        or legacy_session_marker_path(session_id).exists()
    ):
        sys.exit(0)

    if consume_fresh_marker(MARKER_DIR, MARKER_GLOB, FRESHNESS_SECONDS, exclude_prefix=LEGACY_SESSION_MARKER_PREFIX):
        sys.exit(0)

    reason = (
        "[commit-guard] Raw `git commit` is blocked; no part of this call ran, "
        "including any command chained before it. Use the /commit skill instead "
        f"- it writes the session marker this hook checks. If /commit itself is "
        f"broken, set {OVERRIDE_ENV}=1 in this session's environment (settings.json "
        f"\"env\", or exported before launching claude) - an inline prefix on the "
        f"command itself does not reach this hook."
    )
    if ".commit-marker" in command or ".session-markers" in command:
        reason += (
            " This command already tries to write the marker itself: the hook "
            "reads the whole command string before any of it executes, so a "
            "marker chained with `;`/`&&` is never visible in time - write it in "
            "its own tool call first."
        )
    deny(reason)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[commit-guard] hook error, failing open: {e}\n")
        sys.exit(0)
