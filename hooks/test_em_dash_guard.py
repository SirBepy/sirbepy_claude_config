"""Self-test for em-dash-guard.py (todo 307).

Run directly: python hooks/test_em_dash_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "em-dash-guard.py"

_spec = importlib.util.spec_from_file_location("em_dash_guard", _GUARD_PATH)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

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


def run_unit_cases() -> list:
    fails = []
    for text, expect_block, label in UNIT_CASES:
        idx = guard.find_em_dash(text)
        got_block = idx != -1
        ok = got_block == expect_block
        print(f"[{'PASS' if ok else 'FAIL'}] unit: {label}: {text!r} -> {'BLOCK' if got_block else 'PASS'}")
        if not ok:
            fails.append(label)
    return fails


# (payload, expect_block, label) - full-process integration via stdin/stdout,
# so the stop_hook_active loop guard is exercised for real.
INTEGRATION_CASES = [
    ({"last_assistant_message": "clean text"}, False, "integration: clean"),
    ({"last_assistant_message": f"bad{ED}text"}, True, "integration: violation"),
    ({"last_assistant_message": f"bad{ED}text", "stop_hook_active": True}, False, "integration: stop_hook_active suppresses re-block"),
    ({}, False, "integration: missing last_assistant_message key"),
]


def run_integration_cases() -> list:
    fails = []
    for payload, expect_block, label in INTEGRATION_CASES:
        proc = subprocess.run(
            [sys.executable, str(_GUARD_PATH)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
        )
        got_block = '"decision": "block"' in proc.stdout
        ok = got_block == expect_block and proc.returncode == 0
        print(f"[{'PASS' if ok else 'FAIL'}] {label} -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not ok:
            fails.append(label)
    return fails


def run() -> int:
    fails = run_unit_cases() + run_integration_cases()
    print("\nALL PASS" if not fails else f"\nFAILURES: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(run())
