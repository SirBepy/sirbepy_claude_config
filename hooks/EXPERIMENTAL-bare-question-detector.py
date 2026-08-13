"""SPIKE, not installed. Not wired into settings.json. Do not enable.

Prototype for todo 308 (bare-question-stop-hook). Mirrors 307's mechanism:
reads a Stop-shaped payload from stdin, flags a trailing bare question per
the todo's own heuristic (last non-empty line ends in "?", not a
blockquote, no AskUserQuestion tool_use in the same turn per
transcript_path). Never blocks, exit code is always 0. Measurement tool,
not a working guard.

Measured 2026-08-13 against ~4000 real assistant turns pulled from this
machine's own session transcripts across a dozen projects (see the todo
408 report for the corpus and counts): false-positive rate on genuine
non-violations is low, but the trailing-line-only heuristic misses
roughly 1 in 5 real bare-question violations sampled, because Claude
usually closes a multi-option decision with a bulleted list and a
non-question status line ("Nothing is running.", "Say the word."), not a
literal trailing "?". NOT WIRED for that reason: it would give false
confidence without catching most of the real pattern.
"""

import json
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _hooklib import read_payload

STATUS_MARKER_RE = re.compile(r"^<cc-(status|title)[:>].*$", re.IGNORECASE)


def trailing_content_line(text: str):
    for line in reversed((text or "").splitlines()):
        stripped = line.strip()
        if not stripped or STATUS_MARKER_RE.match(stripped):
            continue
        return stripped
    return None


def is_bare_question(text: str) -> bool:
    line = trailing_content_line(text)
    return bool(line) and not line.startswith(">") and line.endswith("?")


def turn_had_auq(transcript_path: str) -> bool:
    """True if an AskUserQuestion tool_use appears anywhere in the assistant
    entries after the most recent user entry (an approximation of "this turn")."""
    path = Path(transcript_path)
    if not path.exists():
        return False
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
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("name") == "AskUserQuestion":
                return True
    return False


def main() -> int:
    payload = read_payload()
    text = payload.get("last_assistant_message") or ""
    if not is_bare_question(text):
        print("CLEAN")
        return 0
    transcript = payload.get("transcript_path") or ""
    if transcript and turn_had_auq(transcript):
        print("EXEMPT_AUQ_IN_TURN")
        return 0
    print(f"FLAG trailing_line={trailing_content_line(text)!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
