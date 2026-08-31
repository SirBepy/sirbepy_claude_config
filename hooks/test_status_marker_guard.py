"""Self-test for status-marker-guard.py.

Run directly: python hooks/test_status_marker_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Covers check()'s pure text scan (colon/XML style, value validation, the
instruction-echo escape hatch), then drives the real guard.main() with
sys.stdin swapped for an in-memory StringIO - no subprocess, no network,
no file I/O. stdin/stdout are restored in a finally block either way.
"""

import io
import sys
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "status-marker-guard.py"
)

# --- check(): malformed style, unrecognised value, instruction echo ---

CHECK_CASES = [
    ("<cc-status:done>", [], "well-formed colon style, no violation"),
    ("<cc-status>done</cc-status>", [], "well-formed XML style, no violation"),
    ("no markers here at all", [], "plain text has nothing to flag"),
    ("<CC-STATUS:done>", [], "case-insensitive tag and closer"),
    (
        "<cc-status:done|question|waiting|working>",
        [],
        "a pipe-joined spec is an instruction echo, never flagged",
    ),
    ("<cc-status:banana>", 1, "unrecognised status value is flagged"),
    ("<cc-status>done", 1, "colon-less open with no closer is malformed"),
    ("<cc-status:done</cc-status>", 1, "colon-open with an XML closer instead of '>' is malformed"),
    ("<cc-title>Foo", 1, "cc-title mixed style is malformed too, no value list"),
    ("<cc-title:Foo>", [], "cc-title well-formed colon style needs no value check"),
]


def check_case(case) -> bool:
    text, expected, label = case
    got = guard.check(text)
    if isinstance(expected, list):
        ok = got == expected
    else:
        ok = len(got) == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (got {got})")
    return ok


fails = _testlib.run_cases(CHECK_CASES, check_case)

# --- main(): stdin/stdout swapped, always restored ---


def run_main(payload_json: str) -> tuple:
    original_stdin, original_stdout = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(payload_json)
    sys.stdout = captured = io.StringIO()
    try:
        guard.main()
        code = 0
    except SystemExit as e:
        code = e.code
    finally:
        sys.stdin = original_stdin
        sys.stdout = original_stdout
    return code, captured.getvalue()


MAIN_CASES = [
    ('{"stop_hook_active": true, "last_assistant_message": "<cc-status:banana>"}', 0, False, "stop_hook_active short-circuits before any scan"),
    ('{"last_assistant_message": ""}', 0, False, "empty message needs no scan"),
    ('{"last_assistant_message": "<cc-status:done>"}', 0, False, "clean marker prints nothing"),
    ('{"last_assistant_message": "<cc-status>done"}', 0, True, "malformed marker prints a block decision"),
]


def check_main(case) -> bool:
    payload_json, expected_code, expect_output, label = case
    code, out = run_main(payload_json)
    ok = code == expected_code and bool(out.strip()) == expect_output
    print(f"{'PASS' if ok else 'FAIL'}: {label} (exit={code}, output={out.strip()!r})")
    return ok


fails += _testlib.run_cases(MAIN_CASES, check_main)

sys.exit(_testlib.summarize(fails, style="count"))
