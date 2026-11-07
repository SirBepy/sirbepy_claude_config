"""PreToolUse hook (todo 1253): a Conductor chat gets a title, once, early.

The title mechanism is the `title` parameter of `report_turn_status`, the
tool every turn already ends with: "only the first one becomes the chat's
visible title, it never changes after". `title` is optional in that tool's
schema, so a turn that omitted it left the chat showing its first-prompt
text in the sidebar and recents (seen 2026-10-27). A prose rule did not fix
that, so this gate does: a `report_turn_status` call without a non-empty
`title` is denied until this session's transcript holds one earlier call
that carried a title. After the first titled call the guard is silent, so
the title is set once and later turns are not taxed.

A denied call without a title is recorded in the transcript but carries no
title, so it never counts as the titled call.

A missing transcript counts as "no title yet": the cost of that is one
retry with a title. Any internal error (bad stdin, unreadable file) fails
open, since this runs on every turn of every Conductor chat.
"""

import json
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    import _hookboot  # retries a shared module another session is mid-way through writing
    from _hooklib import read_payload, deny
except Exception as e:
    sys.stderr.write(f"[chat-title-guard] FATAL: cannot import _hooklib ({e}); failing open.\n")
    sys.exit(0)

TOOL_SUFFIX = "report_turn_status"


def matches_tool(name: str) -> bool:
    suffix = name.rsplit("__", 1)[-1] if "__" in name else name
    return suffix == TOOL_SUFFIX


def has_title(tool_input) -> bool:
    title = tool_input.get("title") if isinstance(tool_input, dict) else None
    return isinstance(title, str) and bool(title.strip())


def transcript_has_titled_call(path: str) -> bool:
    """True when an earlier report_turn_status tool_use in the transcript
    carried a non-empty title. Cheap substring filter first: transcripts run
    to megabytes and almost no line mentions the tool."""
    if not path:
        return False
    p = Path(path)
    if not p.is_file():
        return False
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if TOOL_SUFFIX not in line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = (entry.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if (
                    isinstance(block, dict)
                    and block.get("type") == "tool_use"
                    and matches_tool(str(block.get("name") or ""))
                    and has_title(block.get("input"))
                ):
                    return True
    return False


def main() -> None:
    payload = read_payload()
    if not matches_tool(payload.get("tool_name") or ""):
        sys.exit(0)
    if has_title(payload.get("tool_input")):
        sys.exit(0)
    if transcript_has_titled_call(payload.get("transcript_path") or ""):
        sys.exit(0)
    deny(
        "This chat has no title yet. Call report_turn_status again with a `title`: "
        "2-4 words naming the chat's topic, not its outcome (\"Supabase setup\", not "
        "\"Tailscale removed, committed\"). Only the first title is kept, so it is set once."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[chat-title-guard] hook error, failing open: {e}\n")
        sys.exit(0)
