"""Self-test for croatian-question-guard.py (todo 886).

Run directly: python hooks/test_croatian-question-guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import subprocess
import sys
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "croatian-question-guard.py"
guard = _testlib.load_module("croatian_question_guard", _GUARD_PATH)


# (tool_input, expect_block, label)
SCAN_CASES = [
    (
        {"questions": [{"question": "Which port should the dev server use?", "header": "Port", "options": [{"label": "3000", "description": "default"}]}]},
        False,
        "clean English card",
    ),
    (
        {"questions": [{"question": "Koji ćeš pristup odabrati?", "header": "Pristup", "options": []}]},
        True,
        "diacritic in question field blocks alone",
    ),
    (
        {"questions": [{"question": "Should we ship this?", "header": "Q", "options": [{"label": "da", "description": "ovo nije trebalo"}]}]},
        True,
        "diacritic-free stopwords, 2+ hits blocks",
    ),
    (
        {"questions": [{"question": "bi this be fine?", "header": "Q", "options": []}]},
        False,
        "single stopword hit alone does not block",
    ),
    (
        {"questions": [{"question": "Fine as-is.", "header": "Q", "options": [{"label": "ok", "description": "no issues here"}]}]},
        False,
        "plain English option text stays clean",
    ),
]


def check_scan(case) -> bool:
    tool_input, expect_block, label = case
    got_block = bool(guard.scan(tool_input))
    ok = got_block == expect_block
    print(f"[{'PASS' if ok else 'FAIL'}] scan: {label} -> {'BLOCK' if got_block else 'PASS'}")
    return ok


# (tool_name, expect_match, label)
MATCH_TOOL_CASES = [
    ("AskUserQuestion", True, "built-in tool name"),
    ("mcp__cc_conductor__ask_user_question", True, "MCP tool with server prefix"),
    ("ask_user_question", True, "bare MCP tool name"),
    ("Write", False, "unrelated tool"),
    ("mcp__cc_conductor__send_message", False, "unrelated MCP tool"),
]


def check_match_tool(case) -> bool:
    tool_name, expect_match, label = case
    got = guard.matches_tool(tool_name)
    ok = got == expect_match
    print(f"[{'PASS' if ok else 'FAIL'}] matches_tool: {label} -> {got}")
    return ok


# (tool_name, tool_input, expect_deny, label) - full-process integration via
# stdin/stdout, exit code 2 is the PreToolUse deny signal.
PRE_TOOL_USE_CASES = [
    (
        "AskUserQuestion",
        {"questions": [{"question": "Which config should we use?", "header": "Config", "options": [{"label": "a", "description": "first"}]}]},
        False,
        "AskUserQuestion clean card not denied",
    ),
    (
        "AskUserQuestion",
        {"questions": [{"question": "Koji ćemo pristup koristiti?", "header": "Q", "options": []}]},
        True,
        "AskUserQuestion Croatian card denied",
    ),
    (
        "mcp__cc_conductor__ask_user_question",
        {"questions": [{"question": "Clean question", "header": "Q", "options": [{"label": "da", "description": "nije samo ovo treba"}]}]},
        True,
        "MCP ask_user_question option text denied",
    ),
    (
        "Write",
        {"file_path": "foo.py", "content": "koji ćemo pristup koristiti"},
        False,
        "Write tool stays unscanned",
    ),
    (
        "AskUserQuestion",
        {"questions": [{"question": f"Quoting Joe: 'nije samo ovo' {guard.ESCAPE_MARKER}", "header": "Q", "options": []}]},
        False,
        "escape marker bypasses the whole payload",
    ),
]


def check_pre_tool_use(case) -> bool:
    tool_name, tool_input, expect_deny, label = case
    payload = {"hook_event_name": "PreToolUse", "tool_name": tool_name, "tool_input": tool_input}
    proc = subprocess.run(
        [sys.executable, str(_GUARD_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    got_deny = proc.returncode == 2
    ok = got_deny == expect_deny
    print(f"[{'PASS' if ok else 'FAIL'}] pretooluse: {label} -> exit={proc.returncode} stderr={proc.stderr.strip()!r}")
    return ok


def run() -> int:
    fails = (
        _testlib.run_cases(SCAN_CASES, check_scan)
        + _testlib.run_cases(MATCH_TOOL_CASES, check_match_tool)
        + _testlib.run_cases(PRE_TOOL_USE_CASES, check_pre_tool_use)
    )
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
