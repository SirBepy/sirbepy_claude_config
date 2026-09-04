"""Measure a candidate module's REAL matching functions against a corpus.

Imports the module named by `--module` and calls its own functions - never a
re-declared copy of a pattern under test, because a measurement against a
copy proves the copy matches, not that the shipped code does (phase 2 of the
hook doctrine had to say this explicitly to stop it happening). Prints
per-rule unique/invocation hit counts; `--sample RULE --sample-n N` prints
the FULL text of up to N hits for one rule, since judging a hit as genuine or
noise needs the whole payload, not a truncated one.

NOT a ci/run_all.py check - see tools/extract_corpus.py's docstring for why.

Usage:
    python tools/measure_corpus.py --module hooks/destructive-command-guard.py \\
        --corpus C:\\tmp\\corpus.jsonl --attr CORE_CHECKS
    python tools/measure_corpus.py --module hooks/destructive-command-guard.py \\
        --corpus C:\\tmp\\corpus.jsonl --attr MIDDLE_CHECKS --sample match_git_reset_hard --sample-n 5
    python tools/measure_corpus.py --module some_module.py --corpus C:\\tmp\\corpus.jsonl \\
        --funcs match_foo,match_bar
"""

import argparse
import importlib.util
import json
import sys
from pathlib import Path


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_rules(module, funcs_arg, attr_arg):
    if attr_arg:
        rules = getattr(module, attr_arg)
        return [(fn.__name__, fn) for fn in rules]
    names = [n.strip() for n in funcs_arg.split(",") if n.strip()]
    return [(n, getattr(module, n)) for n in names]


def load_corpus(path: Path, tool_filter):
    rows = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if tool_filter and row.get("tool") not in tool_filter:
                continue
            rows.append(row)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--module", required=True, help="path to the candidate module to measure")
    ap.add_argument("--corpus", required=True, help="JSONL corpus from tools/extract_corpus.py")
    ap.add_argument("--funcs", default=None, help="comma-separated function names in --module, e.g. match_rm_rf,match_git_push_force")
    ap.add_argument("--attr", default=None, help="name of a module-level tuple/list of rule functions, e.g. CORE_CHECKS")
    ap.add_argument("--field", default="payload", help="corpus row field to pass into each rule function (default: payload)")
    ap.add_argument("--tools", default=None, help="comma-separated tool filter, e.g. Bash,PowerShell")
    ap.add_argument("--sample", default=None, help="rule name to print full-text samples for")
    ap.add_argument("--sample-n", type=int, default=10, help="max samples to print with --sample")
    args = ap.parse_args()

    if not args.funcs and not args.attr:
        print("ERROR: pass --funcs or --attr")
        return 2

    module = load_module(Path(args.module))
    rules = resolve_rules(module, args.funcs, args.attr)

    tool_filter = {t.strip() for t in args.tools.split(",") if t.strip()} if args.tools else None
    rows = load_corpus(Path(args.corpus), tool_filter)
    total_unique = len(rows)
    total_invocations = sum(r.get("count", 1) for r in rows)

    print(f"corpus: {total_unique} unique rows, {total_invocations} total invocations\n")

    hits_by_rule = {}
    for name, fn in rules:
        hits = [r for r in rows if fn(r.get(args.field, "")) not in (None, False)]
        hits_by_rule[name] = hits
        invocations = sum(r.get("count", 1) for r in hits)
        print(f"{name:<30} unique={len(hits):<6} invocations={invocations:<6}")

    if args.sample:
        if args.sample not in hits_by_rule:
            print(f"\nERROR: --sample {args.sample!r} is not one of the measured rules: {sorted(hits_by_rule)}")
            return 2
        hits = sorted(hits_by_rule[args.sample], key=lambda r: -r.get("count", 1))
        print(f"\n--- samples for {args.sample} (top {args.sample_n} by count) ---")
        for r in hits[: args.sample_n]:
            print(f"[{r.get('tool')} x{r.get('count', 1)}] {r.get(args.field, '')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
