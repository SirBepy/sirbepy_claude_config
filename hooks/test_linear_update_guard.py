"""Self-test for linear-update-guard.py.

Run directly: python hooks/test_linear_update_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

The point of this guard is what it lets THROUGH: state moves and self-assign must stay
frictionless, or the gate gets bypassed and stops meaning anything.
"""

import json
import os
import subprocess
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
DELETE = "issue" + "Delete"

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

# Deleting a ticket is irreversible to the team and only legal on tickets the dev created,
# which a command string cannot prove, so it always asks regardless of the ground check.
DELETE_CASES = [
    ("Bash", f'curl -X POST "{URL}" -d \'{{"query":"mutation {{ {DELETE}(id:$i) {{ success }} }}"}}\'', True, "issueDelete over the GraphQL endpoint"),
    ("PowerShell", f'Invoke-RestMethod -Uri "{URL}" -Method Post -Body \'{{"query":"mutation {{ {DELETE}(id: 1) {{ success }} }}"}}\'', True, "issueDelete from PowerShell"),
    ("mcp__claude_ai_Linear__delete_issue", None, True, "MCP delete_issue tool"),
    ("mcp__claude_ai_Linear__delete_issue_label", None, False, "deleting a label is not deleting a ticket"),
    ("Bash", f'curl -X POST "{URL}" -d \'{{"query":"mutation {{ {UPDATE}(id:$i, input:{{stateId:$s}}) {{ success }} }}"}}\'', False, "a state move is not a delete"),
    ("Bash", f'curl -X POST "https://example.com/api" -d \'{{"query":"mutation {{ {DELETE}(id:$i) {{ success }} }}"}}\'', False, "mutation name without the Linear endpoint"),
    ("Bash", "git commit -m 'FEAT: linear'", False, "unrelated command"),
    ("Read", None, False, "non-shell tool"),
]


def check_delete(case) -> bool:
    tool_name, command, expected, label = case
    tool_input = {"command": command} if command is not None else {}
    got = guard.is_issue_delete(tool_name, tool_input)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected delete={expected}, got {got})")
    return ok


fails += _testlib.run_cases(DELETE_CASES, check_delete)


def check_delete_asks_end_to_end() -> bool:
    """Through the real script: an issueDelete emits permissionDecision=ask and exits 0, even with
    the ground-check bypass set, since the bypass is for the ground check, not for deletes."""
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": f'curl -X POST "{URL}" -d \'{{"query":"mutation {{ {DELETE}(id:$i) {{ success }} }}"}}\''}})
    env = dict(os.environ, CLAUDE_LINEAR_UPDATE_HOOK_BYPASS="1")
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve().parent / "linear-update-guard.py")],
        input=payload, capture_output=True, text=True, env=env,
    )
    try:
        decision = json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"]
    except (ValueError, KeyError):
        decision = None
    return _testlib.report(proc.returncode == 0 and decision == "ask", f"issueDelete asks end to end (rc={proc.returncode}, decision={decision})")


if not check_delete_asks_end_to_end():
    fails.append("issueDelete asks end to end")
sys.exit(_testlib.summarize(fails, style="count"))
