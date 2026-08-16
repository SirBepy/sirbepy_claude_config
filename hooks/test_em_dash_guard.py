"""Self-test for em-dash-guard.py (todo 307, extended by todo 350).

Run directly: python hooks/test_em_dash_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import subprocess
import sys
import tempfile
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


# (path, input_dict, expected_values, label) - the field-path resolver used
# to pull chat tool args out of a transcript block's `input` dict.
EXTRACT_FIELD_CASES = [
    ("text", {"text": "hi"}, ["hi"], "flat field"),
    ("questions[].question", {"questions": [{"question": "a"}, {"question": "b"}]}, ["a", "b"], "list of dicts"),
    (
        "questions[].options[].description",
        {"questions": [{"options": [{"description": "x"}, {"description": "y"}]}]},
        ["x", "y"],
        "nested list of lists",
    ),
    ("text", {}, [], "missing key"),
]


def check_extract_field(case) -> bool:
    path, tool_input, expected, label = case
    got = guard.extract_field(tool_input, path)
    ok = got == expected
    print(f"[{'PASS' if ok else 'FAIL'}] extract_field: {label} -> {got!r} (expected {expected!r})")
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


def write_transcript(tmpdir: Path, tool_blocks: list) -> Path:
    entries = [
        {"type": "user", "message": {"content": [{"type": "text", "text": "hi"}]}},
    ]
    for name, tool_input in tool_blocks:
        entries.append({
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": name, "input": tool_input}]},
        })
    path = tmpdir / "transcript.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return path


# (tool_blocks, expect_block, label) - transcript-driven tool_use scan
TRANSCRIPT_CASES = [
    (
        [("mcp__cc_conductor__send_message", {"text": f"bad{ED}text"})],
        True,
        "send_message text blocks",
    ),
    (
        [("mcp__cc_conductor__post_message", {"text": f"bad{ED}text"})],
        True,
        "post_message text blocks",
    ),
    (
        [("mcp__cc_conductor__ask_user_question", {"questions": [{"question": f"bad{ED}q", "options": []}]})],
        True,
        "ask_user_question question field blocks",
    ),
    (
        [("mcp__cc_conductor__ask_user_question", {"questions": [{"question": "clean", "options": [{"label": "ok", "description": f"bad{ED}desc"}]}]})],
        True,
        "ask_user_question option description blocks",
    ),
    (
        [("mcp__cc_conductor__send_message", {"text": "all clean"})],
        False,
        "clean chat tool call passes",
    ),
    (
        [("Write", {"file_path": "foo.py", "content": f"# comment{ED}here"})],
        False,
        "Write tool call with em dash in content stays unscanned (scope not widened)",
    ),
    (
        [("mcp__some_other_server__totally_unknown_tool", {"text": f"bad{ED}text"})],
        False,
        "unknown MCP tool stays unscanned",
    ),
]


def run_transcript_cases() -> list:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)

        def check(case):
            tool_blocks, expect_block, label = case
            transcript = write_transcript(tmpdir, tool_blocks)
            payload = {
                "last_assistant_message": "clean final reply",
                "transcript_path": str(transcript),
            }
            proc = subprocess.run(
                [sys.executable, str(_GUARD_PATH)],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
            )
            got_block = '"decision": "block"' in proc.stdout
            ok = got_block == expect_block and proc.returncode == 0
            print(f"[{'PASS' if ok else 'FAIL'}] transcript: {label} -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
            return ok

        return _testlib.run_cases([(*c,) for c in TRANSCRIPT_CASES], check)


def run() -> int:
    fails = (
        _testlib.run_cases(UNIT_CASES, check_unit)
        + _testlib.run_cases(EXTRACT_FIELD_CASES, check_extract_field)
        + _testlib.run_cases(INTEGRATION_CASES, check_integration)
        + run_transcript_cases()
    )
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
