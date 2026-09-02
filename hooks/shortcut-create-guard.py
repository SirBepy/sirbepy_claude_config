"""PreToolUse hook: block Shortcut story CREATION unless the ground check passed.

`/ticket`'s ground check writes `.shortcut-marker-<suffix>` only when
its queries come back clean or soft. A hard-stop signal (a hit in Done/Testing, a merged
PR touching the same file, the asserted symptom already absent at origin) means the
marker is deliberately NOT written, so the create call dies here and the finding has to
go in front of the dev instead. Absence of a marker is the verdict.

REST carries most of the enforcement: SKILL.md says the Shortcut MCP is "frequently not
connected", so nearly every real creation is a curl/Invoke-RestMethod POST.

Deliberately a separate file from `hooks/shortcut-mutation-guard.py`:
that guard fail-closed denies when no `storyPublicId` is present, which is every
not-yet-created story, so adding `stories-create` to its matcher would kill all filing.

Override: set CLAUDE_SHORTCUT_CREATE_HOOK_BYPASS=1 if the ground check itself is broken.
"""

import os
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, consume_fresh_marker, FRESHNESS_SECONDS, OUTBOUND_MARKER_GLOB
except Exception as e:
    sys.stderr.write(f"[shortcut-create-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

MARKER_DIR = _HOOKS_DIR
# Shared with linear-create-guard.py. `.shortcut-marker*` is the legacy name, still accepted
# so instructions written before the 2026-08-18 split keep working.
MARKER_GLOBS = (OUTBOUND_MARKER_GLOB, ".shortcut-marker*")
OVERRIDE_ENV = "CLAUDE_SHORTCUT_CREATE_HOOK_BYPASS"
CREATE_TOOL = "mcp__shortcut__stories-create"

# The lookahead is load-bearing: it keeps `/stories/<id>` (update) and
# `/stories/<id>/comments` out, and `/api/v3/search/stories` never matches at all
# because the path segment order differs.
STORIES_URL_RE = re.compile(r"api\.app\.shortcut\.com/api/v3/stories(?=[\"'\s?&]|$)", re.IGNORECASE)
POST_VERB_RE = re.compile(r"(?:-X\s*POST\b|--request\s+POST\b|-Method\s+[\"']?Post\b)", re.IGNORECASE)
# curl posts on a bare -d unless -G turns the payload into a query string.
DATA_FLAG_RE = re.compile(r"(?:^|\s)(?:-d\b|--data(?:-raw|-binary|-urlencode)?\b)", re.IGNORECASE)
GET_FLAG_RE = re.compile(r"(?:^|\s)(?:-G\b|--get\b)", re.IGNORECASE)


def posts_to_stories(command: str) -> bool:
    if not STORIES_URL_RE.search(command):
        return False
    if POST_VERB_RE.search(command):
        return True
    return bool(DATA_FLAG_RE.search(command)) and not GET_FLAG_RE.search(command)


def is_story_creation(tool_name: str, tool_input: dict) -> bool:
    if tool_name == CREATE_TOOL:
        return True
    if tool_name in ("Bash", "PowerShell"):
        return posts_to_stories(tool_input.get("command", "") or "")
    return False


def main() -> None:
    payload = read_payload()
    tool_name = payload.get("tool_name", "") or ""
    tool_input = payload.get("tool_input") or {}

    if not is_story_creation(tool_name, tool_input):
        sys.exit(0)

    if os.environ.get(OVERRIDE_ENV):
        sys.exit(0)

    if any(consume_fresh_marker(MARKER_DIR, glob, FRESHNESS_SECONDS) for glob in MARKER_GLOBS):
        sys.exit(0)

    deny(
        "[shortcut-create-guard] Ticket creation blocked: no fresh ground-check marker. "
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
        sys.stderr.write(f"[shortcut-create-guard] hook error, failing open: {e}\n")
        sys.exit(0)
