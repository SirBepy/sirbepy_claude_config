#!/usr/bin/env python3
"""Checks the JSON a dashboard card's command prints, before the card is tested live.

Usage: python <your card script> | python check_card_output.py [--paths a,items[0].name,...]
       python check_card_output.py out.json [--paths ...]

Why: the dashboard tool answers a wrong path or non-JSON stdout with a "-" value and no error
(observed 2026-11-07 with `test`), so a broken script looks like a working card with an empty
reading. This prints exactly what is wrong. Exit 0 = fine, 1 = problems listed one per line.

Checks: stdout is one JSON object; each `--paths` entry resolves (dotted, `[n]`, `[]` meaning
the first element of a list); the optional top-level `_card` has only known keys, a headline
string, a `warn`/`good` tone, a `progress` with numeric value and max above 0, and `segments`
whose items are numeric and add up to no more than `max`.
"""

import argparse
import json
import re
import sys

TONES = ("warn", "good")
CARD_KEYS = {"headline", "headline_tone", "progress", "segments"}
TOKEN = re.compile(r"\[(\d*)\]|([^.\[\]]+)")


def resolve(data, path: str):
    """Returns (found, value) for a dotted path with [n] / [] steps."""
    cur = data
    for index, name in TOKEN.findall(path):
        if name:
            if not isinstance(cur, dict) or name not in cur:
                return False, None
            cur = cur[name]
        else:
            if not isinstance(cur, list):
                return False, None
            i = int(index) if index else 0
            if i >= len(cur):
                return False, None
            cur = cur[i]
    return True, cur


def is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def check_card(card) -> list:
    if not isinstance(card, dict):
        return ["_card must be an object"]
    problems = [f"_card.{k} is not a known key ({', '.join(sorted(CARD_KEYS))})" for k in card if k not in CARD_KEYS]
    if "headline" in card and not isinstance(card["headline"], str):
        problems.append("_card.headline must be a string")
    if "headline_tone" in card and card["headline_tone"] not in TONES:
        problems.append(f"_card.headline_tone must be one of {', '.join(TONES)}, got {card['headline_tone']!r}")
    prog = card.get("progress")
    if prog is not None:
        if not isinstance(prog, dict) or not is_num(prog.get("value")) or not is_num(prog.get("max")):
            problems.append("_card.progress needs numeric value and max")
        elif prog["max"] <= 0:
            problems.append("_card.progress.max must be above 0")
    seg = card.get("segments")
    if seg is not None:
        items = seg.get("items") if isinstance(seg, dict) else None
        if not isinstance(items, list) or not items:
            problems.append("_card.segments.items must be a non-empty list")
        elif not is_num(seg.get("max")) or seg["max"] <= 0:
            problems.append("_card.segments.max must be a number above 0")
        else:
            bad = [i for i, it in enumerate(items) if not isinstance(it, dict) or not is_num(it.get("value")) or "label" not in it]
            if bad:
                problems.append(f"_card.segments.items[{bad[0]}] needs a label and a numeric value")
            elif sum(it["value"] for it in items) > seg["max"]:
                problems.append("_card.segments item values add up to more than max, so the bar overflows")
        if isinstance(seg, dict) and seg.get("note_tone") not in (None, *TONES):
            problems.append(f"_card.segments.note_tone must be one of {', '.join(TONES)}")
    return problems


def check(text: str, paths: list) -> list:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return [f"stdout is not a single JSON document ({e}); anything else printed (logs, a banner) must go to stderr"]
    if not isinstance(data, dict):
        return ["top level must be a JSON object, not " + type(data).__name__]
    problems = [f"path {p!r} does not resolve in the output (the card would show '-')" for p in paths if not resolve(data, p)[0]]
    if "_card" in data:
        problems += check_card(data["_card"])
    return problems


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", nargs="?", default="-", help="JSON file, or - for stdin (default)")
    ap.add_argument("--paths", default="", help="comma-separated display paths that must resolve")
    args = ap.parse_args(argv)
    try:
        text = sys.stdin.read() if args.file == "-" else open(args.file, encoding="utf-8").read()
    except OSError as e:
        print(f"check_card_output: cannot read {args.file}: {e}", file=sys.stderr)
        return 2
    paths = [p.strip() for p in args.paths.split(",") if p.strip()]
    problems = check(text, paths)
    for p in problems:
        print("PROBLEM: " + p)
    if not problems:
        print("OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
