"""Self-test for linear-update-guard.py.

Run directly: python hooks/test_linear_update_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

The point of this guard is what it lets THROUGH: state moves and self-assign must stay
frictionless, or the gate gets bypassed and stops meaning anything.
"""

import sys
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "linear-update-guard.py"
)

URL = "https://api.linear.app/graphql"
# Assembled, not literal: the guard matches on the command string, so writing these out
# would make the hook block anyone editing this file.
UPDATE = "issue" + "Update"
COMMENT = "comment" + "Create"
CREATE = "issue" + "Create"

# (tool_name, command, expect_gated, label)
CASES = [
    (
        "Bash",
        f'curl -X POST "{URL}" -d \'{{"query":"mutation {{ {UPDATE}(id:$i, input:{{description:$d}}) {{ success }} }}"}}\'',
        True,
        "issueUpdate rewriting description",
    ),
    (
        "Bash",
        f'curl -X POST "{URL}" -d \'{{"query":"mutation {{ {UPDATE}(id:$i, input:{{title:$t}}) {{ success }} }}"}}\'',
        True,
        "issueUpdate rewriting title",
    ),
    (
        "Bash",
        f'curl -X POST "{URL}" -d \'{{"query":"mutation {{ {COMMENT}(input:{{body:$b}}) {{ success }} }}"}}\'',
        True,
        "a comment is always a claim",
    ),
    ("mcp__claude_ai_Linear__update_issue", None, True, "MCP update_issue tool"),
    # Everything below must stay frictionless.
    (
        "Bash",
        f'curl -X POST "{URL}" -d \'{{"query":"mutation {{ {UPDATE}(id:$i, input:{{stateId:$s}}) {{ success }} }}"}}\'',
        False,
        "moving workflow state asserts nothing",
    ),
    (
        "Bash",
        f'curl -X POST "{URL}" -d \'{{"query":"mutation {{ {UPDATE}(id:$i, input:{{assigneeId:$a}}) {{ success }} }}"}}\'',
        False,
        "self-assign asserts nothing",
    ),
    (
        "Bash",
        f'curl -X POST "{URL}" -d \'{{"query":"query {{ searchIssues(term:$q) {{ nodes {{ title }} }} }}"}}\'',
        False,
        "a read query mentioning title is not an update",
    ),
    (
        "Bash",
        f'curl -X POST "{URL}" -d \'{{"query":"mutation {{ {CREATE}(input:{{title:$t}}) {{ success }} }}"}}\'',
        False,
        "creation is the create guard's job, not this one",
    ),
    (
        "Bash",
        f'curl -X POST "https://api.app.shortcut.com/api/v3/stories/1" -d \'{{"description":"x"}}\'  # {UPDATE}',
        False,
        "mutation name without the Linear endpoint",
    ),
    ("Bash", "git commit -m 'FEAT: linear'", False, "unrelated command"),
    ("Read", None, False, "non-shell tool"),
]


def check(case) -> bool:
    tool_name, command, expected, label = case
    tool_input = {"command": command} if command is not None else {}
    got = guard.needs_ground_check(tool_name, tool_input)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected gated={expected}, got {got})")
    return ok


fails = _testlib.run_cases(CASES, check)
sys.exit(_testlib.summarize(fails, style="count"))
