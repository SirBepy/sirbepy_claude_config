"""PreToolUse hook (todo 998): warns before a question card fires while this
session has dispatched background agents it has not yet seen finish.

The underlying behaviour (answering a question card kills every background
agent in flight) was recorded in a zng-app project memory and violated anyway
on 2026-09-23: 5 background analysis agents died silently when two question
cards fired after them, costing a full re-dispatch. Advisory prose survived
exactly zero turns against the gap between dispatching and asking.

Step 1 of the todo's own Approach is to establish, not assume, whether a
PreToolUse hook can see this session's live-agent state at all. Probed here
by reading a real transcript on this machine
(`~/.claude/projects/C--Users-tecno--claude/
6a91451f-6e11-4038-8231-b93ef93edb89.jsonl`), the same file every hook reads
via `payload["transcript_path"]`:

- A background `Agent` dispatch's own `tool_result` ("Async agent launched
  successfully...") arrives immediately, at dispatch time - it carries no
  completion signal, so tool_result presence can never be the "is it done"
  check (confirmed at that transcript's entries 303-304, 310-315).
- The actual completion signal, observed directly at that transcript's entry
  391, is a LATER `type:"user"`, `isMeta:true` entry whose content string
  contains the literal marker `[Subagent hand-back]` - delivered through the
  same async message channel this harness uses for peer-session
  `post_message` relays, reused here as the loopback for a dispatcher's own
  finished subagent.
- The dispatch's own `tool_use` block never carries that agent's eventual id
  (its `input` keys were only `description`/`model`/`subagent_type`/
  `prompt`/`run_in_background`, confirmed by reading that same transcript),
  so an exact per-agent pairing isn't recoverable from the transcript alone.

Verdict: a hook CAN approximate live-agent count from `transcript_path` -
the same field `hooks/schedulewakeup-guard.py` and
`hooks/send-message-stop-guard.py` already read for comparable inference -
so this hook counts background dispatches seen minus hand-backs seen
(floored at 0) as the live-agent estimate. It is a count, not a per-agent
match, and it only ever over-counts (a hand-back whose marker text this hook
fails to recognise still looks "live"), which is the safer direction for a
warning than silently under-counting.

Advisory only (`allow_with_warning`, never deny): the todo's Acceptance only
asks for "a visible warning... demonstrated once", not a hard gate, and
sometimes the question genuinely matters more than the agents - the
orchestrator is the one positioned to make that call once warned.
"""

import json
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, allow_with_warning
except Exception as e:
    sys.stderr.write(f"[question-card-live-agent-warn] FATAL: cannot import _hooklib ({e}); failing open.\n")
    sys.exit(0)

DISPATCH_TOOLS = ("Agent", "Task")
HANDBACK_MARKER = "[Subagent hand-back]"


def load_transcript_entries(path: str) -> list[dict]:
    entries: list[dict] = []
    if not path:
        return entries
    p = Path(path)
    if not p.exists():
        return entries
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return entries


def is_background_dispatch(block: dict) -> bool:
    """True for an `Agent`/`Task` tool_use block that is background by
    default (Agent tool docs: "Agents run in the background by default") -
    excluded only by an explicit `run_in_background: false`.
    """
    if not isinstance(block, dict) or block.get("type") != "tool_use":
        return False
    if block.get("name") not in DISPATCH_TOOLS:
        return False
    return (block.get("input") or {}).get("run_in_background") is not False


def is_handback_notice(entry: dict) -> bool:
    if entry.get("type") != "user" or not entry.get("isMeta"):
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return HANDBACK_MARKER in content
    if isinstance(content, list):
        return any(
            isinstance(b, dict) and b.get("type") == "text" and HANDBACK_MARKER in (b.get("text") or "")
            for b in content
        )
    return False


def live_agent_count(entries: list[dict]) -> int:
    dispatched = 0
    handed_back = 0
    for entry in entries:
        if entry.get("type") == "assistant":
            for block in (entry.get("message") or {}).get("content") or []:
                if is_background_dispatch(block):
                    dispatched += 1
        elif is_handback_notice(entry):
            handed_back += 1
    return max(0, dispatched - handed_back)


def main() -> None:
    payload = read_payload()
    entries = load_transcript_entries(payload.get("transcript_path") or "")
    if not entries:
        sys.exit(0)

    count = live_agent_count(entries)
    if count <= 0:
        sys.exit(0)

    allow_with_warning(
        f"[question-card-live-agent-warn] This session has {count} more background "
        "agent dispatch(es) than hand-backs seen so far - answering this question "
        "card can kill any that are still running, silently and with no error "
        "(todo 998). Confirm they are actually done before relying on this card's "
        "answer, or wait for them if the work matters."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[question-card-live-agent-warn] hook error, failing open: {e}\n")
        sys.exit(0)
