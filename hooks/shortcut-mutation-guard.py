"""PreToolUse hook that guards Shortcut mutation tools.

Only allows a mutation to proceed if every story the mutation targets has
`requested_by_id` equal to SHORTCUT_OWNER_UUID. Fails closed on any error
(missing token, network failure, malformed response, unknown story-id
key shape) so a bug or schema drift can't silently bypass the guard.

Wired in settings.json as a PreToolUse hook on the Shortcut mutation tools.
SHORTCUT_API_TOKEN and SHORTCUT_OWNER_UUID are read from ~/.claude/.env
(gitignored, not committed).

Exit codes (Claude Code contract):
    0 - allow
    2 - deny (stderr becomes the block reason)
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, consume_fresh_marker, oldest_fresh_marker, FRESHNESS_SECONDS, OUTBOUND_MARKER_GLOB, CLAIM_FIELDS
except Exception as e:
    sys.stderr.write(f"[shortcut-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

API_BASE = "https://api.app.shortcut.com/api/v3"

MARKER_DIR = _HOOKS_DIR
MARKER_GLOBS = (OUTBOUND_MARKER_GLOB, ".shortcut-marker*")

# Only these updates carry a CLAIM, so only these need the ground check. Field list lives
# once in hooks/_hooklib.py's CLAIM_FIELDS (todo 381), not restated here.
CLAIM_BEARING_KEYS = CLAIM_FIELDS["shortcut"]
ENV_FILE = Path.home() / ".claude" / ".env"

# Release custom field UUID. Mutations that touch ONLY this field are allowed
# through without the owner check, so the zirtue-release-backfill skill can
# set release numbers on tickets that were filed by someone else but assigned
# to the dev. See skills/zirtue-release-backfill/SKILL.md.
RELEASE_FIELD_ID = "68f8e559-4a18-4a6e-be1c-fa2f5aaa4fdb"

# Keys in tool_input that may carry a Shortcut story id. Anything matching
# these is treated as a story the mutation targets and must pass the owner
# check. If a matched tool has none of these, we deny fail-closed rather
# than silently allowing the call.
STORY_ID_KEYS = (
    "storyPublicId",
    "story_public_id",
    "storyId",
    "story_id",
    "parentStoryPublicId",
    "parent_story_public_id",
    "subjectStoryPublicId",
    "objectStoryPublicId",
    "subject_id",
    "object_id",
)


def load_env_file(path: Path) -> None:
    """Minimal .env loader. Does NOT overwrite existing env vars.

    utf-8-sig, not utf-8: the live ~/.claude/.env carries a BOM, which made the FIRST key
    parse as '\\ufeffSHORTCUT_API_TOKEN' and never match, denying every mutation.
    """
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def deny(reason: str) -> None:
    sys.stderr.write(f"[shortcut-guard] {reason}\n")
    sys.exit(2)


def allow() -> None:
    sys.exit(0)


def fetch_story(story_id: int, token: str) -> dict:
    req = urllib.request.Request(
        f"{API_BASE}/stories/{story_id}",
        headers={"Shortcut-Token": token, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def is_release_only_mutation(tool_input: dict) -> bool:
    """True if the tool_input changes ONLY the Release custom field.

    Any other key present (name, description, workflow_state_id, etc.), or a
    custom_fields entry for any other field, fails this check so the regular
    owner guard still applies.
    """
    allowed_keys = {"storyPublicId", "custom_fields"}
    extra = set(tool_input.keys()) - allowed_keys
    if extra:
        return False
    cfs = tool_input.get("custom_fields") or []
    if not cfs:
        return False
    return all(cf.get("field_id") == RELEASE_FIELD_ID for cf in cfs)


def is_claim_bearing(tool_name: str, tool_input: dict) -> bool:
    """True if this mutation asserts something about the code, rather than just moving it.

    A comment is always a claim; an update is one only when it rewrites text.
    """
    if tool_name.endswith("create-comment"):
        return True
    return any(tool_input.get(key) for key in CLAIM_BEARING_KEYS)


def extract_story_ids(tool_input: dict) -> list[int]:
    ids: list[int] = []
    for key in STORY_ID_KEYS:
        if key in tool_input and tool_input[key] is not None:
            try:
                ids.append(int(tool_input[key]))
            except (TypeError, ValueError):
                deny(f"tool_input[{key!r}] is not an int: {tool_input[key]!r}")
    return ids


def main() -> None:
    # Via _hooklib so a UTF-8 BOM on stdin is stripped. Parsing it by hand here used to
    # deny every BOM-prefixed payload as malformed, which reads as a guard hit, not a bug.
    try:
        payload = read_payload()
    except Exception as e:
        deny(f"hook received invalid JSON on stdin: {e}")

    tool_name = payload.get("tool_name", "<unknown>")
    tool_input = payload.get("tool_input") or {}
    story_ids = extract_story_ids(tool_input)

    if not story_ids:
        deny(
            f"{tool_name}: no recognized story-id key in tool_input "
            f"(checked {', '.join(STORY_ID_KEYS)}). "
            f"Add the correct key to STORY_ID_KEYS in hooks/shortcut-mutation-guard.py "
            f"before using this tool."
        )

    # Release-only bypass: if the mutation touches ONLY the Release custom
    # field and nothing else, skip the owner check. This lets zirtue-release-
    # backfill update Release on tickets filed by other teammates but owned
    # by the dev.
    if is_release_only_mutation(tool_input):
        allow()

    # Cheap local check before the network-bound owner check below, so a missing marker
    # fails without burning an API round trip per story.
    if is_claim_bearing(tool_name, tool_input):
        if not any(consume_fresh_marker(MARKER_DIR, glob, FRESHNESS_SECONDS) for glob in MARKER_GLOBS):
            deny(
                f"{tool_name} rewrites ticket text, so it needs a ground check: no fresh marker. "
                "Run the ground check in refs/outbound-ground-check.md first. On an update the only "
                "hard stop is the claim being absent at the tracked branch - see its 'Updates are a "
                "different question' section. Moving state or self-assigning needs no check."
            )

    load_env_file(ENV_FILE)
    token = os.environ.get("SHORTCUT_API_TOKEN")
    if not token:
        deny("SHORTCUT_API_TOKEN not set in hook env")

    owner_uuid = os.environ.get("SHORTCUT_OWNER_UUID")
    if not owner_uuid:
        deny("SHORTCUT_OWNER_UUID not set in hook env")

    for story_id in story_ids:
        try:
            story = fetch_story(story_id, token)
        except urllib.error.HTTPError as e:
            deny(f"Shortcut API returned {e.code} for story {story_id}")
        except urllib.error.URLError as e:
            deny(f"Shortcut API unreachable for story {story_id}: {e.reason}")
        except (ValueError, json.JSONDecodeError) as e:
            deny(f"could not parse Shortcut response for story {story_id}: {e}")

        requester = story.get("requested_by_id")
        if requester != owner_uuid:
            name = story.get("name", "<unknown>")
            deny(
                f"refusing to mutate sc-{story_id} '{name}' - "
                f"requested_by_id={requester} is not the owner. "
                f"You may only mutate stories you filed yourself."
            )

    allow()


if __name__ == "__main__":
    main()
