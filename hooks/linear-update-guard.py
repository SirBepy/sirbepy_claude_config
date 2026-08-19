"""PreToolUse hook: block CLAIM-BEARING Linear updates unless the ground check passed.

Sibling of `linear-create-guard.py`, deliberately narrower. An update that only moves
workflow state or self-assigns asserts nothing about the code, so it passes untouched. An
update that rewrites the title or description, or posts a comment, is a claim - and a false
claim on a live ticket is the 2026-08-14 incident wearing different clothes.

The ground check for an update is also narrower than for a create: per
`refs/outbound-ground-check.md`, the only hard stop that carries over is query 3 finding the
claim absent at the tracked branch. "Somebody already did this" is not a reason to stop an
update, because the ticket exists precisely because the work is live.

Known false positive, shared with the other guards: matching is on the command STRING, so a
command that merely mentions the endpoint and mutation name is blocked too. Use the bypass
env var or assemble the string at runtime.

Override: set CLAUDE_LINEAR_UPDATE_HOOK_BYPASS=1 if the ground check itself is broken.
"""

import os
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, consume_fresh_marker, oldest_fresh_marker, FRESHNESS_SECONDS, OUTBOUND_MARKER_GLOB, CLAIM_FIELDS
except Exception as e:
    sys.stderr.write(f"[linear-update-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

MARKER_DIR = _HOOKS_DIR
MARKER_GLOB = OUTBOUND_MARKER_GLOB
OVERRIDE_ENV = "CLAUDE_LINEAR_UPDATE_HOOK_BYPASS"

ENDPOINT_RE = re.compile(r"api\.linear\.app/graphql", re.IGNORECASE)
UPDATE_MUTATION_RE = re.compile(r"\bissueUpdate\b")
COMMENT_MUTATION_RE = re.compile(r"\bcommentCreate\b")
# Built from CLAIM_FIELDS["linear"] in hooks/_hooklib.py (todo 381), not hand-written here.
# `stateId` and `assigneeId` deliberately absent: those are the moves that assert nothing.
CLAIM_FIELD_RE = re.compile(r"\b(" + "|".join(CLAIM_FIELDS["linear"]) + r")\b", re.IGNORECASE)

CLAIM_TOOL_RE = re.compile(r"^mcp__.*linear.*__.*(update_issue|issue.?update|create_comment|comment.?create).*$", re.IGNORECASE)


def is_claim_bearing(command: str) -> bool:
    if not ENDPOINT_RE.search(command):
        return False
    if COMMENT_MUTATION_RE.search(command):
        return True
    return bool(UPDATE_MUTATION_RE.search(command)) and bool(CLAIM_FIELD_RE.search(command))


def needs_ground_check(tool_name: str, tool_input: dict) -> bool:
    if CLAIM_TOOL_RE.match(tool_name):
        return True
    if tool_name in ("Bash", "PowerShell"):
        return is_claim_bearing(tool_input.get("command", "") or "")
    return False


def main() -> None:
    payload = read_payload()
    tool_name = payload.get("tool_name", "") or ""
    tool_input = payload.get("tool_input") or {}

    if not needs_ground_check(tool_name, tool_input):
        sys.exit(0)

    if os.environ.get(OVERRIDE_ENV):
        sys.exit(0)

    if consume_fresh_marker(MARKER_DIR, MARKER_GLOB, FRESHNESS_SECONDS):
        sys.exit(0)

    deny(
        "[linear-update-guard] This Linear write rewrites ticket text, so it needs a ground "
        "check: no fresh marker. Run the ground check in refs/outbound-ground-check.md first. "
        "On an update the only hard stop is the claim being absent at the tracked branch - see "
        "its 'Updates are a different question' section. Moving state or self-assigning needs "
        f"no check. If the ground check itself is broken, set {OVERRIDE_ENV}=1 to bypass."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[linear-update-guard] hook error, failing open: {e}\n")
        sys.exit(0)
