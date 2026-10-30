"""Prints days since the last /global-claude-folder-audit run, as JSON for a dashboard card.

Run: python skills/global-claude-folder-audit/days_since.py [--ledger PATH] [--today YYYY-MM-DD]

Reads the `## Runs` list in ledger.md (one `- YYYY-MM-DD ...` line per completed run) rather
than the dashboard's own last-chat-run timestamp, because a chat that started the audit and
died halfway is not a run: only the skill's final step appends a ledger line.
"""

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

LEDGER = Path(__file__).resolve().parent / "ledger.md"
RUN_LINE = re.compile(r"^- (\d{4}-\d{2}-\d{2})\b")
# The dev's cadence is "every few months"; past ~4 months the card turns amber as the nudge.
WARN_AFTER_DAYS = 120


def run_dates(text: str):
    dates, in_runs = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            in_runs = line.strip().lower() == "## runs"
            continue
        m = RUN_LINE.match(line) if in_runs else None
        if m:
            dates.append(dt.date.fromisoformat(m.group(1)))
    return sorted(dates)


def card(dates, today: dt.date):
    if not dates:
        return {"last_run": None, "days_since": None, "runs": 0,
                "_card": {"headline": "never run", "headline_tone": "warn"}}
    days = (today - dates[-1]).days
    return {"last_run": dates[-1].isoformat(), "days_since": days, "runs": len(dates),
            "_card": {"headline": f"{days} days since last audit",
                      "headline_tone": "warn" if days > WARN_AFTER_DAYS else "good"}}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, default=LEDGER)
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    args = parser.parse_args(argv)
    text = args.ledger.read_text(encoding="utf-8") if args.ledger.is_file() else ""
    print(json.dumps(card(run_dates(text), args.today)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
