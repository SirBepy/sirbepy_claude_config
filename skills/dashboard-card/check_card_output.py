#!/usr/bin/env python3
"""Checks the JSON a dashboard card's command prints, before the card is tested live.

Usage: python check_card_output.py --paths "days_since,items[].n,sum(items[].n)" -- python my_card.py [args]
       python check_card_output.py out.json --paths ...      (a saved copy of the output)
       python check_card_output.py - --paths ... < out.json  (stdin)

Why: the dashboard tool answers a wrong path or non-JSON stdout with a "-" value and no error
(observed 2026-11-07 with `test`), so a broken script looks like a working card with an empty
reading. This prints exactly what is wrong. Quote the --paths value in PowerShell: a bare `(`
starts a subexpression there and the script never runs. Exit 0 = fine, 1 = problems listed one per line,
2 = could not read or run the input.

The `-- command` form runs the script itself and decodes its stdout as UTF-8: piping one native
program into another in PowerShell goes through its text re-encoding layer instead.

Checks: stdout is one JSON object; each `--paths` entry resolves to a non-null value (dotted,
`[n]`, `[]` mapping over every element of a list, `sum(<path>)` over numbers); the optional
top-level `_card` has only known keys, a headline string, a `warn`/`good` tone, a `progress` with
numeric value and max above 0, and `segments` whose items are non-negative numbers. Two checks
are sanity rules of this script, not behaviour probed in the tool: progress value above max and
segment values adding up to more than max.
"""

import argparse
import json
import re
import subprocess
import sys

TONES = ("warn", "good")
CARD_KEYS = {"headline", "headline_tone", "progress", "segments"}
TOKEN = re.compile(r"\[(\d*)\]|([^.\[\]]+)")
SUM = re.compile(r"^sum\((.+)\)$")
# Dotted names with [n] / [] steps only; anything else (`a[x]`, a lone `.`) the tool would not read.
PATH_OK = re.compile(r"^[^.\[\]]+(?:\.[^.\[\]]+|\[\d*\])*$")


def _walk(cur, tokens):
    """Yields every value a path reaches; `[]` fans out over all elements of a list."""
    if not tokens:
        yield cur
        return
    (index, name), rest = tokens[0], tokens[1:]
    if name:
        if isinstance(cur, dict) and name in cur:
            yield from _walk(cur[name], rest)
    elif isinstance(cur, list):
        if index == "":
            for item in cur:
                yield from _walk(item, rest)
        elif int(index) < len(cur):
            yield from _walk(cur[int(index)], rest)


def resolve(data, path: str):
    """Returns (found, value). A null value counts as not found: the card shows '-' for it.

    A path with `[]` returns the list of values it reached; `sum(...)` returns their total.
    """
    m = SUM.match(path)
    inner = m.group(1) if m else path
    if not PATH_OK.match(inner):
        return False, None
    tokens = TOKEN.findall(inner)
    values = [v for v in _walk(data, tokens) if v is not None]
    if m:
        # The tool sums a plain list too (probed 2026-11-07: sum(items) of [1,2,3] shows 6).
        values = [x for v in values for x in (v if isinstance(v, list) else [v])]
        if not values or not all(is_num(v) for v in values):
            return False, None
        return True, sum(values)
    if not values:
        return False, None
    return True, values if any(i == "" and not n for i, n in tokens) else values[0]


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
        elif prog["value"] > prog["max"]:
            problems.append("_card.progress.value is above max, so the bar overfills")
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
            elif any(it["value"] < 0 for it in items):
                problems.append("_card.segments item values must not be negative")
            elif sum(it["value"] for it in items) > seg["max"] + 1e-9:
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
    problems = [f"path {p!r} has no non-null value in the output (the card would show '-')" for p in paths if not resolve(data, p)[0]]
    if "_card" in data:
        problems += check_card(data["_card"])
    return problems


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    command = []
    has_command = "--" in argv
    if has_command:
        i = argv.index("--")
        argv, command = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", nargs="?", default=None, help="JSON file, or - for stdin; omit when using -- command")
    ap.add_argument("--paths", default="", help="comma-separated display paths that must resolve")
    args = ap.parse_args(argv)
    if has_command and not command:
        print("check_card_output: nothing after --; give the card's command, e.g. -- python my_card.py", file=sys.stderr)
        return 2
    try:
        if command:
            # stdin closed so a script that reads it fails fast instead of hanging until the timeout.
            run = subprocess.run(command, capture_output=True, timeout=120, stdin=subprocess.DEVNULL)
            if run.returncode != 0:
                print(f"PROBLEM: command exited {run.returncode}: {run.stderr.decode('utf-8', 'replace').strip()}")
                return 1
            text = run.stdout.decode("utf-8")
        elif args.file in (None, "-"):
            text = sys.stdin.buffer.read().decode("utf-8")
        else:
            with open(args.file, encoding="utf-8") as f:
                text = f.read()
    except (OSError, ValueError, subprocess.SubprocessError) as e:
        print(f"check_card_output: cannot read the card output: {e}", file=sys.stderr)
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
