"""PreToolUse hook: apply the Shortcut requester rule and the Testing ceiling to
raw REST writes made from a Bash/PowerShell command.

`shortcut-mutation-guard.py` only sees the Shortcut MCP tools. On 2026-10-05 a
zng-biller session made 34 state/owner changes through `urllib`/`curl` against
`/api/v3/stories/{id}`, 31 of them on stories johannachen requested, and no
guard saw any of them. Joe's rule (answered 2026-10-07): another requester's
story may be written only when Joe names that ticket in the current session,
and nobody PUTs Ready for deploy (`500018659`) or Complete (`500018258`) by
hand - see skills/ticket/shortcut.md "State ladder".

Scope: a command whose HTTP tool (curl, Invoke-RestMethod/-WebRequest,
wget, or python/node running an inline script) sits at command position and
writes (PUT/POST/PATCH/DELETE, or curl data without -G) to
`api.app.shortcut.com/api/v3/stories/<id>[/...]`. Story creation (no id) is
`shortcut-create-guard.py`'s. A write issued from inside a script FILE is not
visible in the command string; that is the stated limit.

Exempt: a session whose real user turns invoked `/zirtue-release-backfill` or
`/shortcut-done-audit`, the two skills whose job is to set Release on and
close other people's stories.

Fails closed when a write is detected but the requester cannot be verified
(no token, network error), matching shortcut-mutation-guard.py. Set
CLAUDE_SHORTCUT_RAW_WRITE_BYPASS=1 if the guard itself is broken.
"""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, is_tool_result_entry, is_injected_user_entry
    _spec = importlib.util.spec_from_file_location("_shortcut_mutation_guard", _HOOKS_DIR / "shortcut-mutation-guard.py")
    _mutation_guard = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mutation_guard)
    fetch_story = _mutation_guard.fetch_story
    load_env_file = _mutation_guard.load_env_file
    ENV_FILE = _mutation_guard.ENV_FILE
except Exception as e:
    sys.stderr.write(f"[shortcut-raw-write-guard] FATAL: cannot import helpers ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

OVERRIDE_ENV = "CLAUDE_SHORTCUT_RAW_WRITE_BYPASS"
CEILING_STATE_IDS = ("500018659", "500018258")
EXEMPT_SKILLS = ("/zirtue-release-backfill", "/shortcut-done-audit")

STORY_ID_RE = re.compile(r"api\.app\.shortcut\.com/api/v3/stories/(\d+)", re.IGNORECASE)
HTTP_TOOL_RE = re.compile(
    r"\b(?:curl(?:\.exe)?|invoke-restmethod|invoke-webrequest|irm|iwr|wget|python3?|py|node)\b",
    re.IGNORECASE,
)
# Command position, plus `=` so `$r = Invoke-RestMethod ...` counts.
COMMAND_START_RE = re.compile(r"(?:^|[|;&(){\n=])\s*$")
WRITE_VERB_RE = re.compile(
    r"(?:-X\s*|--request\s+)[\"']?(?:PUT|POST|PATCH|DELETE)\b"
    r"|-Method\s+[\"']?(?:Put|Post|Patch|Delete)\b"
    r"|method\s*=\s*[\"'](?:PUT|POST|PATCH|DELETE)[\"']"
    r"|requests\.(?:put|post|patch|delete)\(",
    re.IGNORECASE,
)
DATA_FLAG_RE = re.compile(r"(?:^|\s)(?:-d\b|--data(?:-raw|-binary|-urlencode)?\b)", re.IGNORECASE)
GET_FLAG_RE = re.compile(r"(?:^|\s)(?:-G\b|--get\b)", re.IGNORECASE)


def written_story_ids(command: str) -> list[int]:
    """Story ids a shell command writes to, or [] if it is not a write."""
    ids = [int(m) for m in STORY_ID_RE.findall(command)]
    if not ids:
        return []
    if not any(COMMAND_START_RE.search(command[: m.start()]) for m in HTTP_TOOL_RE.finditer(command)):
        return []
    writes = WRITE_VERB_RE.search(command) or (DATA_FLAG_RE.search(command) and not GET_FLAG_RE.search(command))
    return sorted(set(ids)) if writes else []


def real_user_texts(transcript_path: str) -> list[str]:
    path = Path(transcript_path or "")
    if not transcript_path or not path.is_file():
        return []
    texts = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "user" or is_tool_result_entry(entry) or is_injected_user_entry(entry):
                continue
            content = (entry.get("message", {}) or {}).get("content")
            if isinstance(content, str):
                texts.append(content)
            elif isinstance(content, list):
                texts.append("\n".join(b.get("text", "") for b in content if isinstance(b, dict)))
    return texts


def named_in_session(story_id: int, texts: list[str]) -> bool:
    pattern = re.compile(rf"(?<!\d)(?:sc-)?{story_id}(?!\d)", re.IGNORECASE)
    return any(pattern.search(t) for t in texts)


def main() -> None:
    payload = read_payload()
    if payload.get("tool_name") not in ("Bash", "PowerShell"):
        sys.exit(0)
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    story_ids = written_story_ids(command)
    if not story_ids or os.environ.get(OVERRIDE_ENV):
        sys.exit(0)

    texts = real_user_texts(payload.get("transcript_path", ""))
    if any(skill in t for t in texts for skill in EXEMPT_SKILLS):
        sys.exit(0)

    if any(state in command for state in CEILING_STATE_IDS):
        deny(
            "[shortcut-raw-write-guard] This write sets Ready for deploy or Complete by hand. Testing "
            "(500018257) is the ceiling for Joe and Claude: QA promotes from Testing and "
            "/zirtue-release-backfill closes. See skills/ticket/shortcut.md \"State ladder\"."
        )

    unnamed = [sid for sid in story_ids if not named_in_session(sid, texts)]
    if not unnamed:
        sys.exit(0)

    load_env_file(ENV_FILE)
    token = os.environ.get("SHORTCUT_API_TOKEN")
    owner = os.environ.get("SHORTCUT_OWNER_UUID")
    if not token or not owner:
        deny(f"[shortcut-raw-write-guard] cannot verify the requester of sc-{unnamed[0]}: SHORTCUT_API_TOKEN or SHORTCUT_OWNER_UUID not set.")

    for sid in unnamed:
        try:
            story = fetch_story(sid, token)
        except Exception as e:
            deny(f"[shortcut-raw-write-guard] cannot verify the requester of sc-{sid} ({e}); refusing the write.")
        if story.get("requested_by_id") != owner:
            deny(
                f"[shortcut-raw-write-guard] refusing a raw write to sc-{sid} '{story.get('name', '?')}': "
                "someone else requested it and Joe has not named it in this session. Ask Joe, or "
                "route it through /ticket."
            )

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[shortcut-raw-write-guard] hook error, failing open: {e}\n")
        sys.exit(0)
