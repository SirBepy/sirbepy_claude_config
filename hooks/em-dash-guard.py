"""Stop hook (todo 307): block a turn whose final assistant message contains
a literal em dash (U+2014). CLAUDE.md bans the character outright, and
`last_assistant_message` is already scoped to Claude's own composed text
(tool_use/tool_result are separate content blocks, never folded in), so an
exact codepoint match has no meaningful false-positive surface here.

Built from chr(0x2014), never a literal em dash, so this file can never
trip its own check or em-dash.sh's commit-time scan.
"""

import json
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


def find_em_dash(text: str) -> int:
    return text.find(EM_DASH) if text else -1


def build_reason(text: str, idx: int) -> str:
    start = max(0, idx - 20)
    end = min(len(text), idx + 21)
    snippet = text[start:end].replace("\n", " ")
    return (
        "Em dash (U+2014) found in your reply near: \"...%s...\". Global rule "
        "bans it outright, rewrite using a comma, colon, or hyphen instead." % snippet
    )


def main() -> None:
    payload = read_payload()
    if payload.get("stop_hook_active") is True:
        sys.exit(0)
    text = payload.get("last_assistant_message") or ""
    idx = find_em_dash(text)
    if idx == -1:
        sys.exit(0)
    print(json.dumps({"decision": "block", "reason": build_reason(text, idx)}))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[em-dash-guard] hook error, failing open: {e}\n")
        sys.exit(0)
