"""Two hook events, one module (todo 307, extended by todo 350 and 892):
block an em dash (U+2014) in Claude-authored chat prose. CLAUDE.md bans the
character outright.

Stop: scans the turn's final assistant message plus any allowlisted MCP
chat tool call already run this turn - the retroactive half, since a chat
tool call has already delivered by the time Stop fires.

PreToolUse: scans a single allowlisted chat tool call's own `tool_input`
before it reaches the host, denying so the message never sends (todo 892).
Gated on `hook_event_name` so the two arms share one field allowlist and
one character definition without one running twice.

`last_assistant_message` only ever carries Claude's own composed text
(tool_use/tool_result are separate content blocks), so an exact codepoint
match has no meaningful false-positive surface there. Tool call args are a
different story: `Write`/`Edit` file content and `Bash` command strings can
legitimately quote external text containing an em dash, so those stay
unscanned (todo 307's scope decision, not reopened here). Only the
CHAT_TOOL_TEXT_FIELDS allowlist below is scanned, since that content is
Claude-authored chat prose a user or peer session reads verbatim.

Built from chr(0x2014), never a literal em dash, so this file can never
trip its own check or em-dash.sh's commit-time scan.
"""

import json
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny, is_tool_result_entry, iter_turn_tool_uses
except Exception as e:
    sys.stderr.write(f"[em-dash-guard] FATAL: cannot import _hooklib ({e}); failing open.\n")
    sys.exit(0)

EM_DASH = chr(0x2014)

# Chat-content tool allowlist (todo 350), keyed by tool-name suffix after the
# last "__" so any MCP server prefix exposing a same-named tool is caught
# too. Each value is a list of field-path specs into `input`: "." for a dict
# key, "[]" to iterate a list.
CHAT_TOOL_TEXT_FIELDS = {
    "send_message": ["text"],
    "post_message": ["text"],
    "update_message": ["text"],
    "ask_user_question": [
        "questions[].question",
        "questions[].header",
        "questions[].options[].label",
        "questions[].options[].description",
    ],
}

_PATH_TOKEN_RE = re.compile(r"\[\]|[^.\[\]]+")


def find_em_dash(text: str) -> int:
    return text.find(EM_DASH) if text else -1


def build_reason(text: str, idx: int, source: str = "your reply", already_sent: bool = False) -> str:
    start = max(0, idx - 20)
    end = min(len(text), idx + 21)
    snippet = text[start:end].replace("\n", " ")
    repair = (
        " That message already reached its recipient; revise it with "
        "mcp__cc_conductor__update_message (newest ordinal first)." if already_sent else ""
    )
    return (
        "Em dash (U+2014) found in %s near: \"...%s...\". Global rule "
        "bans it outright, rewrite using a comma, colon, or hyphen instead.%s" % (source, snippet, repair)
    )


def extract_field(tool_input: dict, path: str):
    """Walk one field-path spec against a tool's input dict, returning every
    string leaf value it resolves to (0, 1, or many for a "[]" segment)."""
    values = [tool_input]
    for tok in _PATH_TOKEN_RE.findall(path):
        next_values = []
        if tok == "[]":
            for v in values:
                if isinstance(v, list):
                    next_values.extend(v)
        else:
            for v in values:
                if isinstance(v, dict) and tok in v:
                    next_values.append(v[tok])
        values = next_values
    return [v for v in values if isinstance(v, str)]


def tool_call_texts(name: str, tool_input: dict):
    """Yield (source_label, text) for text-bearing args of one chat-content
    tool call, per the CHAT_TOOL_TEXT_FIELDS allowlist. Shared by the Stop
    arm's transcript scan and the PreToolUse arm's direct payload scan."""
    suffix = name.rsplit("__", 1)[-1] if "__" in name else name
    field_paths = CHAT_TOOL_TEXT_FIELDS.get(suffix)
    if not field_paths:
        return
    for field_path in field_paths:
        for value in extract_field(tool_input, field_path):
            yield f"{name} ({field_path})", value


def chat_tool_texts(transcript_path: str):
    """Yield (source_label, text) for text-bearing args of this turn's
    allowlisted chat-content tool calls already run (Stop arm, retroactive)."""
    for name, tool_input in iter_turn_tool_uses(transcript_path):
        yield from tool_call_texts(name, tool_input)


def handle_pre_tool_use(payload: dict) -> None:
    """Deny a single chat tool call before it reaches the host (todo 892)."""
    tool_name = payload.get("tool_name") or ""
    tool_input = payload.get("tool_input") or {}
    for source, text in tool_call_texts(tool_name, tool_input):
        idx = find_em_dash(text)
        if idx != -1:
            deny(build_reason(text, idx, source))
    sys.exit(0)


def handle_stop(payload: dict) -> None:
    if payload.get("stop_hook_active") is True:
        sys.exit(0)

    # (source, text, already_sent) - transcript-scanned tool calls already
    # delivered by the time Stop fires; last_assistant_message has too, but
    # carries no update_message-revisable identity, so it stays unmarked.
    sources = [("your reply", payload.get("last_assistant_message") or "", False)]
    transcript_path = payload.get("transcript_path") or ""
    if transcript_path:
        sources.extend((s, t, True) for s, t in chat_tool_texts(transcript_path))

    for source, text, already_sent in sources:
        idx = find_em_dash(text)
        if idx != -1:
            reason = build_reason(text, idx, source, already_sent=already_sent)
            print(json.dumps({"decision": "block", "reason": reason}))
            sys.exit(0)
    sys.exit(0)


def main() -> None:
    payload = read_payload()
    if payload.get("hook_event_name") == "PreToolUse":
        handle_pre_tool_use(payload)
        return
    handle_stop(payload)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[em-dash-guard] hook error, failing open: {e}\n")
        sys.exit(0)
