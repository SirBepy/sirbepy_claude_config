"""Data dump and mechanical checks for /grill. STUB: real signatures and CLI, neutral returns.

The real implementation replaces this file; the stub exists so every test in
test_grill_dump.py can be proven red against it (spec section 9).
"""

import argparse
import sys


def parse_decisions(text, path):
    return []


def sum_usage(parent_lines, subagent_line_lists):
    return {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0,
            "input_equiv": 0, "wall_s": 0, "first_ts": None, "last_ts": None}


def chat_kind(uuid, card_subs, finish_subs):
    return "main"


def cluster(entries, include_refs=(), cap=40):
    return []


def complaint_hits(path, scope, window_start, window_end, is_stem):
    return []


def git_outcome(repo, since):
    return []


def phase0(archive_dir, scopes):
    return []


def verify_receipt(r):
    return None


def gate(rows, clusters, rundir, scopes, projects_dir, allow_all_keep):
    return 0, ""


def main(argv=None):
    parser = argparse.ArgumentParser(prog="grill_dump.py")
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("dump")
    d.add_argument("--scope", required=True)
    d.add_argument("--days", type=int, default=30)
    d.add_argument("--now")
    d.add_argument("--include-refs", default="")
    d.add_argument("--projects-dir")
    d.add_argument("--decisions-dir")
    d.add_argument("--digests-dir")
    d.add_argument("--archive-dir")
    d.add_argument("--out", required=True)
    c = sub.add_parser("check-receipts")
    c.add_argument("rows")
    g = sub.add_parser("gate")
    g.add_argument("rows")
    g.add_argument("--clusters", required=True)
    g.add_argument("--scope", required=True)
    g.add_argument("--projects-dir")
    g.add_argument("--allow-all-keep")
    k = sub.add_parser("cost")
    k.add_argument("--session", required=True)
    k.add_argument("--projects-dir")
    parser.parse_args(argv)
    return 0


if __name__ == "__main__":
    sys.exit(main())
