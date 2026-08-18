"""PreToolUse hook: block Linear issue CREATION unless the ground check passed.

Sibling of `shortcut-create-guard.py`, same mechanism, different platform. The ground
check in `refs/outbound-ground-check.md` writes `.outbound-marker-<suffix>` only when its
queries come back clean or soft. A hard-stop signal (a hit already in a done-equivalent
state, a merged PR touching the same file, the asserted symptom already absent at origin)
means the marker is deliberately NOT written, so the create call dies here and the finding
goes in front of the dev instead. Absence of a marker is the verdict.

One guard per platform on purpose, rather than one guard with many matchers: a regex
mistake here can only disarm Linear, never Shortcut.

Detection differs from the Shortcut guard in one way worth stating. GraphQL sends every
operation as a POST to a single endpoint, so the HTTP verb carries no signal at all - the
mutation NAME is the only thing separating a create from a read. Hence the `issueCreate`
match rather than any POST-detection.

Known false positive, shared with the Shortcut guard: matching is on the command STRING, so
any command that merely mentions the endpoint and the mutation name is blocked too - writing
a test for this hook trips it. Use the bypass env var for that, or build the string at runtime.

Override: set CLAUDE_LINEAR_CREATE_HOOK_BYPASS=1 if the ground check itself is broken.
"""

import os
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, consume_fresh_marker, oldest_fresh_marker
except Exception as e:
    sys.stderr.write(f"[linear-create-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

MARKER_DIR = _HOOKS_DIR
MARKER_GLOB = ".outbound-marker*"
FRESHNESS_SECONDS = 120
OVERRIDE_ENV = "CLAUDE_LINEAR_CREATE_HOOK_BYPASS"

ENDPOINT_RE = re.compile(r"api\.linear\.app/graphql", re.IGNORECASE)
# `issueCreate` is the mutation; the word boundary keeps `issueCreateAttachment`-style
# neighbours out. Linear has no second spelling for filing an issue.
CREATE_MUTATION_RE = re.compile(r"\bissueCreate\b")
# The MCP server names creation tools this way; matched separately since an MCP call
# carries no command string to regex.
CREATE_TOOL_RE = re.compile(r"^mcp__.*linear.*__.*(create_issue|issue.?create).*$", re.IGNORECASE)


def posts_issue_create(command: str) -> bool:
    return bool(ENDPOINT_RE.search(command)) and bool(CREATE_MUTATION_RE.search(command))


def is_issue_creation(tool_name: str, tool_input: dict) -> bool:
    if CREATE_TOOL_RE.match(tool_name):
        return True
    if tool_name in ("Bash", "PowerShell"):
        return posts_issue_create(tool_input.get("command", "") or "")
    return False


def main() -> None:
    payload = read_payload()
    tool_name = payload.get("tool_name", "") or ""
    tool_input = payload.get("tool_input") or {}

    if not is_issue_creation(tool_name, tool_input):
        sys.exit(0)

    if os.environ.get(OVERRIDE_ENV):
        sys.exit(0)

    if consume_fresh_marker(MARKER_DIR, MARKER_GLOB, FRESHNESS_SECONDS):
        sys.exit(0)

    deny(
        "[linear-create-guard] Linear issue creation blocked: no fresh ground-check marker. "
        "Run the ground check in refs/outbound-ground-check.md first. "
        "If it returned a HARD STOP, that is the point - the work may already be done; "
        "put the hit in front of the dev instead of filing. "
        f"If the ground check itself is broken, set {OVERRIDE_ENV}=1 to bypass."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[linear-create-guard] hook error, failing open: {e}\n")
        sys.exit(0)
