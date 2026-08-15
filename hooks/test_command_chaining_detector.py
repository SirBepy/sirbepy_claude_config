"""Self-test for EXPERIMENTAL-command-chaining-detector.py (todo 311 spike).

Run directly: python hooks/test_command_chaining_detector.py
Exits 0 on all-pass, 1 on any failure. This tests the spike's own logic
only - it does NOT certify the spike as safe to wire, see its docstring
and the todo 311 report for the measured false-positive rate.
"""

import sys
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
spike = _testlib.load_module(
    "chaining_spike", _HOOKS_DIR / "EXPERIMENTAL-command-chaining-detector.py"
)

# (command, expect_flag, label). Drawn from real commands seen in this
# machine's own session transcripts (todo 311 corpus, 30047 samples).
CASES = [
    ("git diff | awk '{print}' | sort | uniq -c", False, "pipeline only, no chain"),
    ('cd "C:/Users/tecno/Desktop/Projects/zng-app" && flutter test', True,
     "real corpus: cd-scoping idiom - FLAGGED but this is the dominant real false-positive class"),
    ("find . -iname a.txt; find . -iname b.txt", True, "real corpus: two independent finds, genuine chain"),
    ('for f in a.ts b.ts; do echo "=== $f ==="; grep -n foo "$f"; done', True,
     "real corpus: bash for-loop `;` is loop syntax, not chaining - FALSE POSITIVE"),
    ('$t = (Get-Content token -Raw).Trim(); Invoke-RestMethod -Headers @{Authorization="Bearer $t"}', True,
     "real corpus: PowerShell variable-sharing one-liner, state can't persist across calls - FALSE POSITIVE"),
    ("git commit -m \"fix: a; b still works\"", False, "semicolon inside a quoted commit message"),
    ("echo hi || true", True, "fallback idiom, still a real `||` chain by this detector's rule"),
    ("git log --oneline -5", False, "single command, nothing to flag"),
]


def check(case) -> bool:
    cmd, expect_flag, label = case
    got_flag = bool(spike.find_chain_ops(cmd))
    ok = got_flag == expect_flag
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: {cmd!r} -> {'FLAG' if got_flag else 'CLEAN'}")
    return ok


def run() -> int:
    fails = _testlib.run_cases(CASES, check)
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
