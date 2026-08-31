"""Self-test for flutter-workdir-guard.py.

Run directly: python hooks/test_flutter_workdir_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Covers the todo-803 addition (fvm/flutter/dart as the LEADING word of a
Bash-tool command is denied outright, PowerShell untouched) by driving the
real guard.main() with a monkeypatched read_payload - no subprocess, no
live fvm/flutter/dart, no network. The pre-existing destructive-flag/pin
logic already has coverage via done/380-era manual verification and is not
re-covered here beyond confirming this addition does not break its pass-
through cases.
"""

import os
import sys
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "flutter-workdir-guard.py"
)


def run_main(tool_name: str, command: str) -> int:
    guard.read_payload = lambda: {"tool_name": tool_name, "tool_input": {"command": command}}
    try:
        guard.main()
        return 0
    except SystemExit as e:
        return e.code


# (tool_name, command, expected exit code, label)
CASES = [
    ("Bash", "fvm flutter analyze", 2, "fvm flutter analyze via Bash is denied"),
    ("PowerShell", "fvm flutter analyze", 0, "fvm flutter analyze via PowerShell passes through untouched"),
    ("Bash", "flutter analyze", 2, "bare flutter via Bash is denied"),
    ("Bash", "dart test", 2, "bare dart via Bash is denied"),
    ("Bash", "grep flutter README.md", 0, "grep flutter README.md via Bash is allowed, not leading"),
    ("Bash", 'echo "run fvm"', 0, "echo run fvm via Bash is allowed, not leading and quoted"),
    (
        "Bash",
        "cd C:/repo && fvm flutter test",
        2,
        "fvm leading its own chained segment after cd is still denied",
    ),
    ("Bash", "git commit -m 'fix'", 0, "unrelated command via Bash is allowed"),
]


def check(case) -> bool:
    tool_name, command, expected, label = case
    got = run_main(tool_name, command)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected exit={expected}, got {got})")
    return ok


saved_bypass = os.environ.pop(guard.OVERRIDE_ENV, None)
try:
    fails = _testlib.run_cases(CASES, check)
finally:
    if saved_bypass is not None:
        os.environ[guard.OVERRIDE_ENV] = saved_bypass

sys.exit(_testlib.summarize(fails, style="count"))
