"""PreToolUse hook: block git WRITE ops when the Bash/PowerShell shell cwd
has drifted out of the session's actual project.

Real incident 2026-09-02: a zng-app session `cd`'d into ~/.claude to read a
memory file, and the shell cwd stayed there across the next tool call. A
bare `git push` meant for zng-app's develop pushed sirbepy_claude_config
master instead, `f707e2d..5910374`, published with no prompt or error.
Undoing a wrong push needs a force-push, so this fires BEFORE the command,
mirroring hooks/flutter-workdir-guard.py's shape for the same drift bug.

payload["cwd"] tracks the live, drifting Bash/PowerShell cwd (see
ui-screenshot-reminder.py's own note on the same field); $CLAUDE_PROJECT_DIR
is the harness's fixed project root for the whole session (Claude Code sets
this for every hook, per plugin-dev's hook-development docs). A WRITE
subcommand is blocked only when the two resolve to different git repo
roots. Read-only git (status/log/diff/show/rev-parse/ls-remote/...) is
never touched - cross-repo reads are routine. A `cd`/Set-Location earlier in
the SAME command, or an explicit `git -C <path>` before the subcommand,
pins the effective cwd and bypasses the check for that segment.

Override: set CLAUDE_GIT_WORKDIR_GUARD_BYPASS=1 to bypass if this hook
itself misfires.
"""

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, strip_quotes
except Exception as e:
    sys.stderr.write(f"[git-workdir-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

OVERRIDE_ENV = "CLAUDE_GIT_WORKDIR_GUARD_BYPASS"
GIT_TIMEOUT_SECONDS = 10

GIT_BASENAMES = {"git", "git.exe"}
WRITE_SUBCOMMANDS = {"push", "commit", "reset", "checkout", "restore", "update-ref", "rebase", "stash"}
# Global git flags that consume a following value token, so the subcommand
# scan never mistakes a flag's value for the subcommand itself.
VALUE_FLAGS = {"-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}
CD_WORDS = {"cd", "cd.", "chdir", "pushd", "sl", "set-location", "push-location"}

ABS_PATH_RE = re.compile(r"^(?:[A-Za-z]:[\\/]|\\\\|/[^/\s])")
CHAIN_SPLIT_RE = re.compile(r"&&|\|\||;|\n|\|")


def tokenize(segment: str) -> list[str]:
    try:
        return [strip_quotes(t) for t in shlex.split(segment, posix=False)]
    except ValueError:
        return []


def basename(tok: str) -> str:
    return re.split(r"[\\/]", tok)[-1].lower()


def pinned_cd(tokens: list[str]) -> str | None:
    """Absolute path of a cd/Set-Location/Push-Location in this segment, if
    any - scans the 3 tokens after the cd-word so a `-Path` flag in between
    doesn't hide the value.
    """
    for i, tok in enumerate(tokens):
        if tok.lower() not in CD_WORDS:
            continue
        for cand in tokens[i + 1 : i + 4]:
            if ABS_PATH_RE.match(cand):
                return cand
    return None


def git_write_subcommand(tokens: list[str]) -> tuple[bool, str | None]:
    """Return (pinned, subcommand) for a `git ...` token list. `pinned` is
    True iff a global `-C <path>` appears before the subcommand - the
    explicit, deliberate repo-pin case (matches /commit's own `git -C
    <path>` rule) - so a subcommand-level `-C` (e.g. `git commit -C HEAD`,
    a different flag entirely) is never mistaken for it.
    """
    if not tokens or basename(tokens[0]) not in GIT_BASENAMES:
        return False, None
    i = 1
    pinned = False
    while i < len(tokens):
        tok = tokens[i]
        if tok == "-C":
            pinned = True
            i += 2
            continue
        low = tok.lower()
        if low == "-c" or low.split("=", 1)[0] in VALUE_FLAGS:
            i += 1 if "=" in tok else 2
            continue
        if tok.startswith("-"):
            i += 1
            continue
        break
    sub = tokens[i].lower() if i < len(tokens) else None
    return pinned, (sub if sub in WRITE_SUBCOMMANDS else None)


def repo_root(path: str) -> str | None:
    if not path or not os.path.isdir(path):
        return None
    try:
        result = subprocess.run(
            ["git", "-C", path, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not command.strip():
        sys.exit(0)
    if os.environ.get(OVERRIDE_ENV):
        sys.exit(0)

    effective_cwd = payload.get("cwd") or ""
    write_hit = False
    for segment in CHAIN_SPLIT_RE.split(command):
        tokens = tokenize(segment)
        if not tokens:
            continue

        pinned, sub = git_write_subcommand(tokens)
        if sub and not pinned:
            write_hit = True
            break
        if sub and pinned:
            break

        cd_pin = pinned_cd(tokens)
        if cd_pin:
            effective_cwd = cd_pin

    if not write_hit:
        sys.exit(0)

    shell_root = repo_root(effective_cwd)
    harness_root = repo_root(os.environ.get("CLAUDE_PROJECT_DIR") or "")

    # Can't determine one side - fail open rather than block on a guess.
    if not shell_root or not harness_root:
        sys.exit(0)

    if norm(shell_root) == norm(harness_root):
        sys.exit(0)

    deny(
        "[git-workdir-guard] Blocked: this git write command's shell is inside "
        f"'{shell_root}', but this session's project is '{harness_root}' - the "
        "shell cwd likely drifted from an earlier `cd`. A wrong-repo push "
        "published silently once already (2026-09-02). Re-run with "
        f"`git -C {harness_root} <command>`, or cd back to the project first. "
        f"Bypass: set {OVERRIDE_ENV}=1."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[git-workdir-guard] hook error, failing open: {e}\n")
        sys.exit(0)
