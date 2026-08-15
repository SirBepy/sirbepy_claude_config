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

Override: set CLAUDE_PR_HOOK_BYPASS=1 to bypass if /create-pr is broken.
"""

import os
import shlex
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, consume_fresh_marker
except Exception as e:
    sys.stderr.write(f"[pr-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

MARKER_DIR = _HOOKS_DIR
MARKER_GLOB = ".pr-marker*"
FRESHNESS_SECONDS = 120
OVERRIDE_ENV = "CLAUDE_PR_HOOK_BYPASS"
MUTATING_ACTIONS = {"create", "edit"}

# Flags that consume a separate following token as their value, e.g.
# `gh --repo owner/name pr create ...`.
VALUE_FLAGS = {"-R", "--repo", "--hostname"}


def gh_pr_action(command: str) -> str | None:
    """Return the `gh pr <action>` word if `command` invokes one, else None.

    Token-based: walks past global flags (skipping their values for flags
    like -R) to find "pr", then past pr's own flags to find the action word,
    so quoted text or paths containing "pr create" never match.
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
                return tokens[k]
    return None


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""

    action = gh_pr_action(command)
    if action not in MUTATING_ACTIONS:
        sys.exit(0)

    if os.environ.get(OVERRIDE_ENV):
        sys.exit(0)

    if consume_fresh_marker(MARKER_DIR, MARKER_GLOB, FRESHNESS_SECONDS):
        sys.exit(0)

    deny(
        f"[pr-guard] Raw `gh pr {action}` is blocked. Use the /create-pr "
        "skill instead - it writes the authorisation marker this hook "
        f"checks, after its tiering/anti-bloat rules and preview/approval "
        f"gate. If /create-pr itself is broken, set {OVERRIDE_ENV}=1 to bypass."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[pr-guard] hook error, failing open: {e}\n")
        sys.exit(0)
