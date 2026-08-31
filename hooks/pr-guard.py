"""PreToolUse hook: block raw `gh pr create` / `gh pr edit` outside /create-pr.

Fires on every Bash/PowerShell call. Detects a mutating `gh pr` subcommand via
token-aware parsing (not string search), so `gh pr view`, `gh pr list`, and
similar read-only calls always pass through untouched. The /create-pr skill
writes a uniquely-suffixed marker file (`.pr-marker-<suffix>`) immediately
before each real `gh pr create`/`gh pr edit` call; this hook only lets the
call through if at least one fresh matching marker exists, then deletes
exactly the oldest fresh one - this way two concurrent sessions each get
their own marker and can't consume each other's. Fails open on any hook
error so a bug here can never permanently wedge every PR in every repo.

`gh pr comment` / `gh pr review` are deliberately NOT gated here - they are
/code-review --comment's own mechanism for posting inline review comments,
a separate workflow from /create-pr's body tiering/anti-bloat/preview gate
that this todo targets, so blocking them would break that skill for no
bypass-prevention benefit.

Override: set CLAUDE_PR_HOOK_BYPASS=1 in this session's environment
(settings.json "env", or exported before launching claude) to bypass if
/create-pr is broken - an inline prefix on the command itself does not reach
this hook.
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
    sys.stderr.write(f"[pr-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

MARKER_DIR = _HOOKS_DIR
MARKER_GLOB = ".pr-marker*"
OVERRIDE_ENV = "CLAUDE_PR_HOOK_BYPASS"
# Must be set in this session's environment (settings.json "env", or exported
# before launching claude); an inline `VAR=1 <cmd>` prefix never reaches this
# hook, since PreToolUse reads the command string before any shell parses it.
MUTATING_ACTIONS = {"create", "edit"}

# Every GitHub account the dev pushes under; gh-account-switch.sh picks one per
# repo remote, so an edit can arrive authenticated as any of them.
OWNER_LOGINS = {"josipmuzic", "JosipMuzicZirtue", "JosipMuzicFibo", "SirBepy"}

# Flags that consume a separate following token as their value, e.g.
# `gh --repo owner/name pr create ...`.
VALUE_FLAGS = {"-R", "--repo", "--hostname"}


def gh_pr_action(command: str) -> tuple[str, str | None] | None:
    """Return `(action, target)` if `command` invokes `gh pr <action>`, else None.

    Token-based: walks past global flags (skipping their values for flags
    like -R) to find "pr", then past pr's own flags to find the action word,
    so quoted text or paths containing "pr create" never match. `target` is
    the positional after the action (PR number/URL/branch), None if absent.
    """
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        # Unbalanced quotes etc. - can't safely tokenize; don't block on a guess.
        return None

    for i, tok in enumerate(tokens):
        if tok != "gh":
            continue
        j = i + 1
        while j < len(tokens) and tokens[j].startswith("-"):
            if tokens[j] in VALUE_FLAGS and "=" not in tokens[j]:
                j += 2
            else:
                j += 1
        if j < len(tokens) and tokens[j] == "pr":
            k = j + 1
            while k < len(tokens) and tokens[k].startswith("-"):
                k += 1
            if k < len(tokens):
                target = tokens[k + 1] if k + 1 < len(tokens) and not tokens[k + 1].startswith("-") else None
                return tokens[k], target
    return None


def cd_target(command: str) -> str | None:
    """Return the path from a leading `cd <path>` in `command`, if any."""
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return None
    for i, tok in enumerate(tokens):
        if tok == "cd" and i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
            return tokens[i + 1]
    return None


def pr_is_owned(target: str | None, cwd: str | None, command: str) -> bool:
    """True when the PR `target` names was opened by one of OWNER_LOGINS.

    Editing the dev's own PR (retitle, add a Fixes line, fix a sentence a
    reviewer flagged) is not what /create-pr's body gate exists to police.
    Anything unprovable - lookup fails, no auth, someone else's PR - is False,
    so the marker requirement still applies.
    """
    # gh ships as a shim CreateProcess won't find on PATH alone, and the payload
    # does not always carry cwd, so resolve both rather than assuming either.
    gh = shutil.which("gh") or shutil.which("gh.exe")
    if not gh:
        return False
    args = [gh, "pr", "view", "--json", "author", "--jq", ".author.login"]
    if target:
        args.insert(3, target)
    for candidate in (cwd, cd_target(command), os.getcwd()):
        if not candidate or not os.path.isdir(candidate):
            continue
        try:
            out = subprocess.run(
                args, cwd=candidate, capture_output=True, text=True, timeout=20
            )
        except Exception:
            continue
        if out.returncode == 0 and out.stdout.strip() in OWNER_LOGINS:
            return True
    return False


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""

    parsed = gh_pr_action(command)
    action, target = parsed if parsed else (None, None)
    if action not in MUTATING_ACTIONS:
        sys.exit(0)

    if os.environ.get(OVERRIDE_ENV):
        sys.exit(0)

    # Marker check first: it is a local mtime read, while pr_is_owned() spends up
    # to 20s per candidate cwd on a `gh pr view`. A /create-pr edit already has a
    # marker, so the common path must never pay that.
    if consume_fresh_marker(MARKER_DIR, MARKER_GLOB, FRESHNESS_SECONDS):
        sys.exit(0)

    if action == "edit" and pr_is_owned(target, payload.get("cwd"), command):
        sys.exit(0)

    deny(
        f"[pr-guard] Raw `gh pr {action}` is blocked. Use the /create-pr "
        "skill instead - it writes the authorisation marker this hook "
        f"checks, after its tiering/anti-bloat rules and preview/approval "
        f"gate. If /create-pr itself is broken, set {OVERRIDE_ENV}=1 in this "
        f"session's environment (settings.json \"env\", or exported before "
        f"launching claude) - an inline prefix on the command itself does not "
        f"reach this hook."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[pr-guard] hook error, failing open: {e}\n")
        sys.exit(0)
