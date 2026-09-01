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

Prefilter re-check (todo 844): once a marker allows the commit, this hook
also re-runs `skills/commit/prefilter-gate.sh` itself over the commit's own
`-- <paths>` pathspec, so a `;` (which ignores exit status) between an
earlier gate call and `git commit` can no longer let a flagged diff land -
the gate's verdict is recomputed here, at commit time, independent of how
the caller chained the shell command. A pathspec-less commit or a gate that
can't be invoked at all fails open, same philosophy as the rest of this file.
"""

import os
import shlex
import shutil
import subprocess
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

# Shell operators that can follow a `git commit` invocation in a chained
# command; a pathspec scan must stop at these, never swallow tokens from a
# following command as if they were commit paths.
_CHAIN_OPERATORS = {";", "&&", "||"}

PREFILTER_GATE_SCRIPT = _HOOKS_DIR.parent / "skills" / "commit" / "prefilter-gate.sh"


def _tokenize(command: str) -> list[str] | None:
    try:
        return shlex.split(command, posix=True)
    except ValueError:
        # Unbalanced quotes etc. - can't safely tokenize; don't block on a guess.
        return None


def _commit_subcommand_index(tokens: list[str]) -> int | None:
    """Index of the `commit` token in a `git commit` invocation, walking past
    global flags (skipping their values for flags like -C), or None."""
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
            return j
    return None


def is_git_commit_invocation(command: str) -> bool:
    """True if `command` contains a real `git commit` subcommand call.

    Token-based: walks past global flags (skipping their values for flags
    like -C) to find the actual subcommand word, so `commit-graph`,
    `--grep="commit"`, or a path/message containing "commit" never match.
    """
    tokens = _tokenize(command)
    if tokens is None:
        return False
    return _commit_subcommand_index(tokens) is not None


def extract_commit_pathspec(tokens: list[str]) -> list[str] | None:
    """Paths named after a `--` separator in the `git commit` invocation
    found in `tokens`, or None if there's no such separator to resolve
    (e.g. no explicit pathspec). Stops at a chain operator so a command
    riding after the commit is never read as more paths.
    """
    idx = _commit_subcommand_index(tokens)
    if idx is None:
        return None
    k = idx + 1
    while k < len(tokens) and tokens[k] not in _CHAIN_OPERATORS:
        if tokens[k] == "--":
            paths = []
            m = k + 1
            while m < len(tokens) and tokens[m] not in _CHAIN_OPERATORS:
                paths.append(tokens[m])
                m += 1
            return paths
        k += 1
    return None


def resolve_bash() -> str | None:
    """Locate a POSIX-capable bash for running prefilter-gate.sh.

    On Windows, `bash` on PATH can resolve to the System32 WSL launcher
    instead of Git for Windows' bash - proven here to silently fail on a
    `C:/...` script path (WSL treats it as a Linux-side relative path that
    doesn't exist). Prefer the bash co-located with the resolved `git.exe`.
    """
    if os.name != "nt":
        return shutil.which("bash")
    git_exe = shutil.which("git")
    if git_exe:
        candidate = Path(git_exe).resolve().parent.parent / "bin" / "bash.exe"
        if candidate.exists():
            return str(candidate)
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files (x86)\Git\bin\bash.exe",
    ):
        if Path(candidate).exists():
            return candidate
    return None


def run_prefilter_gate(paths: list[str], cwd: str) -> int | None:
    """Re-run prefilter-gate.sh over `paths`, independent of the caller's own
    shell chaining (todo 844). Returns the gate's exit code, or None if it
    could not be invoked at all - fails open rather than wedging every commit
    on an infra problem (missing bash, missing script, timeout).
    """
    if not PREFILTER_GATE_SCRIPT.exists():
        return None
    bash = resolve_bash()
    if not bash:
        return None
    try:
        result = subprocess.run(
            [bash, str(PREFILTER_GATE_SCRIPT), *paths],
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.returncode


def session_marker_path(session_id: str) -> Path:
    return SESSION_MARKER_DIR / session_id


def legacy_session_marker_path(session_id: str) -> Path:
    """Pre-split location - read-only fallback for a marker written before
    the `.session-markers/` move (todo 341)."""
    return MARKER_DIR / f"{LEGACY_SESSION_MARKER_PREFIX}{session_id}"


def _deny_prefilter_failure() -> None:
    deny(
        "[commit-guard] This commit's own prefilter-gate re-check just failed "
        "(comment-noise/em-dash/comment-tense/secret-scan); no part of this call "
        "ran, including any command chained before it. A `;` between an earlier "
        "gate run and `git commit` does not skip this - the gate is re-run here, "
        "at commit time, over the exact pathspec being committed. Run `bash "
        "~/.claude/skills/commit/prefilter-gate.sh <files>` to see the full "
        "flagged output, fix it, then retry."
    )


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""

    if not is_git_commit_invocation(command):
        sys.exit(0)

    if os.environ.get(OVERRIDE_ENV):
        sys.exit(0)

    tokens = _tokenize(command) or []

    session_id = payload.get("session_id") or ""
    if session_id and (
        session_marker_path(session_id).exists()
        or legacy_session_marker_path(session_id).exists()
    ):
        paths = extract_commit_pathspec(tokens)
        if paths and run_prefilter_gate(paths, payload.get("cwd") or "") == 1:
            _deny_prefilter_failure()
        sys.exit(0)

    if consume_fresh_marker(MARKER_DIR, MARKER_GLOB, FRESHNESS_SECONDS, exclude_prefix=LEGACY_SESSION_MARKER_PREFIX):
        paths = extract_commit_pathspec(tokens)
        if paths and run_prefilter_gate(paths, payload.get("cwd") or "") == 1:
            _deny_prefilter_failure()
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
