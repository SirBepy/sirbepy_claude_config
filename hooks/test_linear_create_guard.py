"""Self-test for linear-create-guard.py.

Run directly: python hooks/test_linear_create_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

import _testlib
from _hooklib import oldest_fresh_marker

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "linear-create-guard.py"
)

URL = "https://api.linear.app/graphql"
# Assembled, not written literally: the guard matches on the command string, so a literal
# endpoint-plus-mutation in this file would make the hook block anyone editing it.
CREATE = "issue" + "Create"
UPDATE = "issue" + "Update"

# (tool_name, command, expect_creation, label)
CASES = [
    ("Bash", f'curl -X POST "{URL}" -d \'{{"query":"mutation {{ {CREATE}(input: $i) {{ success }} }}"}}\'', True, "curl POST issueCreate mutation"),
    ("PowerShell", f'Invoke-RestMethod -Uri "{URL}" -Method Post -Body $q  # {CREATE}', True, "IRM issueCreate"),
    ("mcp__claude_ai_Linear__create_issue", None, True, "MCP create_issue tool"),
    # Everything below must pass through untouched.
    ("Bash", f'curl -X POST "{URL}" -d \'{{"query":"query {{ searchIssues(term: $q) {{ nodes {{ id }} }} }}"}}\'', False, "a read query, same endpoint and verb"),
    ("Bash", f'curl -X POST "{URL}" -d \'{{"query":"mutation {{ {UPDATE}(id: $i) {{ success }} }}"}}\'', False, "issueUpdate is not creation"),
    ("Bash", f'curl -X POST "https://api.app.shortcut.com/api/v3/stories" -d @p.json  # {CREATE}', False, "mutation name without the Linear endpoint"),
    ("Bash", f'echo "we call {CREATE} somewhere"', False, "mutation name in prose, no endpoint"),
    ("Bash", "git commit -m 'FEAT: linear'", False, "unrelated command"),
    ("Read", None, False, "non-shell tool"),
]


def check(case) -> bool:
    tool_name, command, expected, label = case
    tool_input = {"command": command} if command is not None else {}
    got = guard.is_issue_creation(tool_name, tool_input)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected creation={expected}, got {got})")
    return ok


fails = _testlib.run_cases(CASES, check)

# This guard takes the shared marker only; the legacy Shortcut name must not satisfy it.
with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    fresh = tmpdir / ".outbound-marker-abc"
    fresh.touch()
    if not _testlib.report(
        oldest_fresh_marker(tmpdir, guard.MARKER_GLOB, guard.FRESHNESS_SECONDS) is not None,
        "fresh shared marker is found",
    ):
        fails.append("fresh shared marker is found")

    stale_time = time.time() - (guard.FRESHNESS_SECONDS + 60)
    os.utime(fresh, (stale_time, stale_time))
    label = f"marker older than {guard.FRESHNESS_SECONDS}s is ignored"
    if not _testlib.report(
        oldest_fresh_marker(tmpdir, guard.MARKER_GLOB, guard.FRESHNESS_SECONDS) is None, label
    ):
        fails.append(label)
    fresh.unlink()

    for name in (".shortcut-marker-legacy", ".commit-marker-session-xyz"):
        (tmpdir / name).touch()
        label = f"{name} never satisfies the Linear guard"
        if not _testlib.report(
            oldest_fresh_marker(tmpdir, guard.MARKER_GLOB, guard.FRESHNESS_SECONDS) is None,
            label,
        ):
            fails.append(label)
        (tmpdir / name).unlink()

sys.exit(_testlib.summarize(fails, style="count"))
