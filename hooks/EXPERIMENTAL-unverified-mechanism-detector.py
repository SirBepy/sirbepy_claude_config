"""SPIKE, not installed. Not wired into settings.json. Do not enable.

Prototype for todo 270 (unverified-mechanism-rule-third-repeat), Half B.

Reads a Stop/SubagentStop-shaped JSON payload from stdin, pulls
`last_assistant_message` (per code.claude.com/docs/en/hooks: this field
exists specifically because transcript_path can lag the current turn),
and regex-flags assertive-causal phrasing so a human can eyeball the
false-positive rate. Never blocks - exit code is always 0. This is a
measurement tool, not a working guard.
"""

import json
import re
import sys

ASSERTIVE_PATTERN = re.compile(
    r"\b("
    r"because|causes?|due to|results? in|"
    r"so\s+\w+(?:\s+\w+){0,3}\s+(?:happens|gets|is|refuses|blocks|fails|works)|"
    r"the reason (?:is|why)|"
    r"verified|confirmed"
    r")\b",
    re.IGNORECASE,
)

HEDGE_PATTERN = re.compile(
    r"\bunverified\b|\bmy best guess\b|\bhypothesis\b|\bhaven'?t (checked|verified)\b",
    re.IGNORECASE,
)


def main() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw.lstrip("﻿") or "{}")
    except json.JSONDecodeError:
        print("PARSE_ERROR")
        return 0

    text = payload.get("last_assistant_message", "")
    hits = ASSERTIVE_PATTERN.findall(text)
    hedged = bool(HEDGE_PATTERN.search(text))

    if hits and not hedged:
        print(f"FLAG matches={sorted(set(h.lower() for h in hits))}")
    elif hits and hedged:
        print(f"HEDGED matches={sorted(set(h.lower() for h in hits))}")
    else:
        print("CLEAN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
