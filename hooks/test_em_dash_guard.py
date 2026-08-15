"""Self-test for em-dash-guard.py (todo 307).

Run directly: python hooks/test_em_dash_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import subprocess
import sys
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "em-dash-guard.py"
guard = _testlib.load_module("em_dash_guard", _GUARD_PATH)

ED = chr(0x2014)

# (text, expect_block, label)
UNIT_CASES = [
    ("Here is a plain summary with no violations.", False, "clean prose"),
    ("", False, "empty string"),
    (f"Two options{ED} pick one.", True, "literal em dash in prose"),
    ("The rule bans U+2014 (spelled out, not the raw codepoint).", False, "spelled-out reference, no literal char"),
    (f"```\nfoo{ED}bar\n```", True, "literal em dash inside a fenced code block"),
    (f"one{ED}two{ED}three", True, "multiple em dashes, first one reported"),
    ("plain hyphen - and en dash – are fine", False, "sibling dash characters not flagged"),
]


def check_unit(case) -> bool:
    text, expect_block, label = case
    idx = guard.find_em_dash(text)
    got_block = idx != -1
    ok = got_block == expect_block
    print(f"[{'PASS' if ok else 'FAIL'}] unit: {label}: {text!r} -> {'BLOCK' if got_block else 'PASS'}")
    return ok


# (payload, expect_block, label) - full-process integration via stdin/stdout,
# so the stop_hook_active loop guard is exercised for real.
INTEGRATION_CASES = [
    ({"last_assistant_message": "clean text"}, False, "integration: clean"),
    ({"last_assistant_message": f"bad{ED}text"}, True, "integration: violation"),
    ({"last_assistant_message": f"bad{ED}text", "stop_hook_active": True}, False, "integration: stop_hook_active suppresses re-block"),
    ({}, False, "integration: missing last_assistant_message key"),
]


def check_integration(case) -> bool:
    payload, expect_block, label = case
    proc = subprocess.run(
        [sys.executable, str(_GUARD_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    got_block = '"decision": "block"' in proc.stdout
    ok = got_block == expect_block and proc.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] {label} -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
    return ok


def run() -> int:
    fails = _testlib.run_cases(UNIT_CASES, check_unit) + _testlib.run_cases(INTEGRATION_CASES, check_integration)
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
