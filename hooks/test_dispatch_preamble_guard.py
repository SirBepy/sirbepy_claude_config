"""Self-test for dispatch-preamble-guard.py.

Run directly: python hooks/test_dispatch_preamble_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import sys
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "dispatch-preamble-guard.py"
)

STAGING = "Stage your changes but do NOT commit. The main agent will run /commit after your report-back."
BACKGROUND = "`run_in_background` is FORBIDDEN in builder subagents"
SCREENSHOT = "save them under `.for_bepy/screenshots/12345-6789/`"
FULL_PROMPT = f"{STAGING}\n\n{BACKGROUND}\n\n{SCREENSHOT}\n\nDo the task."

# (prompt, expect_missing_nonempty, label)
CASES = [
    (FULL_PROMPT, False, "all three markers present"),
    (FULL_PROMPT.replace(STAGING, ""), True, "staging line missing"),
    (FULL_PROMPT.replace(BACKGROUND, ""), True, "run_in_background/FORBIDDEN line missing"),
    (FULL_PROMPT.replace(SCREENSHOT, ""), True, "screenshot id line missing"),
    (f"{STAGING}\n\n{BACKGROUND}\n\nREAD-ONLY DISPATCH\n\nDo the task.", False, "READ-ONLY DISPATCH opts out of screenshot marker"),
    ("do the thing, no markers at all", True, "nothing present"),
]


def check(case) -> bool:
    prompt, expect_missing_nonempty, label = case
    missing = guard.missing_markers(prompt)
    got = bool(missing)
    ok = got == expect_missing_nonempty
    print(f"{'PASS' if ok else 'FAIL'}: {label} (missing={missing})")
    return ok


fails = _testlib.run_cases(CASES, check)

# tool_name filtering: only Agent/Task dispatches are inspected at all.
for name in ("Agent", "Task"):
    if not _testlib.report(name in guard.DISPATCH_TOOLS, f"{name} is a recognized dispatch tool"):
        fails.append(f"{name} recognized")

for name in ("Bash", "Read", "Edit", "PowerShell"):
    if not _testlib.report(name not in guard.DISPATCH_TOOLS, f"{name} passes through untouched"):
        fails.append(f"{name} untouched")

sys.exit(_testlib.summarize(fails, style="count"))
