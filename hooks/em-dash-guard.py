"""Stop hook (todo 307, extended by todo 350): block a turn whose final
assistant message, OR whose text-bearing args on an allowlisted MCP chat
tool call this turn, contain a literal em dash (U+2014). CLAUDE.md bans the
character outright.

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
    from _hooklib import read_payload
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


def build_reason(text: str, idx: int, source: str = "your reply") -> str:
    start = max(0, idx - 20)
    end = min(len(text), idx + 21)
    snippet = text[start:end].replace("\n", " ")
    return (
        "Em dash (U+2014) found in %s near: \"...%s...\". Global rule "
        "bans it outright, rewrite using a comma, colon, or hyphen instead." % (source, snippet)
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


def iter_turn_tool_uses(transcript_path: str):
    """Yield (name, input) for tool_use blocks in assistant entries after the
    most recent user entry, an approximation of "this turn"."""
    path = Path(transcript_path)
    if not path.exists():
        return
    entries = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    last_user_idx = -1
    for i, e in enumerate(entries):
        if e.get("type") == "user":
            last_user_idx = i
    for e in entries[last_user_idx + 1:]:
        if e.get("type") != "assistant":
            continue
        content = (e.get("message", {}) or {}).get("content", []) or []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield block.get("name") or "", (block.get("input") or {})


def chat_tool_texts(transcript_path: str):
    """Yield (source_label, text) for text-bearing args of this turn's
    allowlisted chat-content tool calls."""
    for name, tool_input in iter_turn_tool_uses(transcript_path):
        suffix = name.rsplit("__", 1)[-1] if "__" in name else name
        field_paths = CHAT_TOOL_TEXT_FIELDS.get(suffix)
        if not field_paths:
            continue
        for field_path in field_paths:
            for value in extract_field(tool_input, field_path):
                yield f"{name} ({field_path})", value


def main() -> None:
    payload = read_payload()
    if payload.get("stop_hook_active") is True:
        sys.exit(0)

    sources = [("your reply", payload.get("last_assistant_message") or "")]
    transcript_path = payload.get("transcript_path") or ""
    if transcript_path:
        sources.extend(chat_tool_texts(transcript_path))

    for source, text in sources:
        idx = find_em_dash(text)
        if idx != -1:
            print(json.dumps({"decision": "block", "reason": build_reason(text, idx, source)}))
            sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[em-dash-guard] hook error, failing open: {e}\n")
        sys.exit(0)
