"""PreToolUse guard: block/warn ScheduleWakeup calls outside /loop.

Hard-blocks only the one detectable misuse shape (pending background
Bash/Agent dispatch this turn, no /loop marker anywhere in the transcript);
everything else warns but allows. Exit 0 = allow, exit 2 = deny (stderr =
reason). See memory feedback_schedulewakeup_loop_only.
"""

import json
import re
import sys
from pathlib import Path

COMMAND_NAME_RE = re.compile(r"<command-name>\s*/?([a-zA-Z0-9_-]+)\s*</command-name>", re.IGNORECASE)
BG_TOOL_NAMES = {"Bash", "Agent"}

MEMORY_HINT = (
    "feedback_schedulewakeup_loop_only: ScheduleWakeup is scoped to /loop "
    "dynamic-pacing mode. For a background Bash/Agent task, wait for the "
    "task-notification instead of polling with ScheduleWakeup."
)


def allow(message: str = "") -> None:
    if message:
        print(message)
    sys.exit(0)


def deny(reason: str) -> None:
    sys.stderr.write(f"[schedulewakeup-guard] {reason}\n")
    sys.exit(2)


def load_transcript_entries(path: str) -> list[dict]:
    entries: list[dict] = []
    try:
        text = Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return entries
    for raw in text.splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            entries.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return entries


def find_command_names(entries: list[dict]) -> set[str]:
    names: set[str] = set()
    for entry in entries:
        content = (entry.get("message") or {}).get("content")
        blocks = content if isinstance(content, list) else [{"type": "text", "text": content}]
        for block in blocks:
            text = block.get("text", "") if isinstance(block, dict) else ""
            names.update(m.group(1).lower() for m in COMMAND_NAME_RE.finditer(text or ""))
    return names


def is_human_authored(entry: dict) -> bool:
    if entry.get("type") != "user" or entry.get("isMeta"):
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return True
    # A "user" entry made ONLY of tool_result blocks is a synthetic tool-result
    # turn, not a human message - it must not anchor the turn boundary.
    return any(isinstance(b, dict) and b.get("type") != "tool_result" for b in content or [])


def last_user_turn_index(entries: list[dict]) -> int:
    for i in range(len(entries) - 1, -1, -1):
        if is_human_authored(entries[i]):
            return i
    return 0


def has_pending_background_dispatch(entries: list[dict], since_index: int) -> bool:
    for entry in entries[since_index:]:
        if entry.get("type") != "assistant":
            continue
        for block in (entry.get("message") or {}).get("content") or []:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            if block.get("name") in BG_TOOL_NAMES and (block.get("input") or {}).get("run_in_background") is True:
                return True
    return False


def main() -> None:
    try:
        payload = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        allow()

    transcript_path = payload.get("transcript_path")
    entries = load_transcript_entries(transcript_path) if transcript_path else []
    if not entries:
        allow()

    # Trust ANY /loop invocation anywhere in this session's transcript - a
    # false "not in /loop" read must never block a real /loop wakeup.
    if "loop" in find_command_names(entries):
        allow()

    turn_start = last_user_turn_index(entries)
    if has_pending_background_dispatch(entries, turn_start):
        deny(
            "ScheduleWakeup called with a run_in_background Bash/Agent dispatch "
            "this turn and no /loop invocation found in this session. " + MEMORY_HINT
        )

    allow(
        "[schedulewakeup-guard] No /loop invocation detected in this session. "
        + MEMORY_HINT + " If this genuinely is a /loop wakeup, proceeding is fine."
    )


if __name__ == "__main__":
    main()
