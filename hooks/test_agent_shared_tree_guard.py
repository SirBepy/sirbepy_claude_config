"""Self-test for agent-shared-tree-guard.py (todo 990).

Run directly: python hooks/test_agent_shared_tree_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import subprocess
import sys
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "agent-shared-tree-guard.py"
guard = _testlib.load_module("agent_shared_tree_guard", _GUARD_PATH)

AGENT_PAYLOAD_BASE = {"agent_id": "aaaeae68dcacc2c9d", "agent_type": "general-purpose"}
ORCHESTRATOR_PAYLOAD_BASE = {"session_id": "top-level-session"}

# (payload agent fields, expected bool, label)
AGENT_CALL_CASES = [
    ({"agent_id": "aaaeae68dcacc2c9d", "agent_type": "general-purpose"}, True, "agent_id + agent_type present -> agent call"),
    ({"agent_id": "aaaeae68dcacc2c9d"}, True, "agent_id present alone is still enough"),
    ({}, False, "neither key present -> orchestrator"),
    ({"agent_id": ""}, False, "empty-string agent_id is falsy, not a real id"),
]


def check_agent_call(case) -> bool:
    payload, expected, label = case
    got = guard.is_agent_call(payload)
    ok = got == expected
    print(f"[{'PASS' if ok else 'FAIL'}] is_agent_call: {label} -> {got}")
    return ok


def run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_GUARD_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


# (extra payload fields, command, expect_code, label) - the four acceptance cases plus edges.
INTEGRATION_CASES = [
    (
        AGENT_PAYLOAD_BASE, "git stash push -u", 2,
        "acceptance 1: subagent git stash push is refused",
    ),
    (
        AGENT_PAYLOAD_BASE, "git stash", 2,
        "bare git stash (defaults to push) is refused for a subagent",
    ),
    (
        ORCHESTRATOR_PAYLOAD_BASE, "git stash push -u", 0,
        "acceptance 2a: orchestrator's own git stash is unaffected",
    ),
    (
        ORCHESTRATOR_PAYLOAD_BASE, "git reset --soft abc1234", 0,
        "acceptance 2b: /commit fold's reset --soft (orchestrator-run) is unaffected",
    ),
    (
        AGENT_PAYLOAD_BASE, "git checkout main", 0,
        "acceptance 3a: git checkout <branch> still works for a subagent",
    ),
    (
        AGENT_PAYLOAD_BASE, "git checkout -- README.md", 2,
        "acceptance 3b: git checkout -- <path> is refused for a subagent",
    ),
    (
        AGENT_PAYLOAD_BASE, "git reset --hard HEAD~1", 2,
        "subagent git reset (any form) is refused",
    ),
    (
        AGENT_PAYLOAD_BASE, "git reset --soft abc1234", 2,
        "subagent git reset --soft is refused too - /commit fold never runs as a subagent",
    ),
    (
        AGENT_PAYLOAD_BASE, "git status", 0,
        "read-only git is never touched",
    ),
    (
        AGENT_PAYLOAD_BASE, "git log && git stash push", 2,
        "a chained command still catches the stash in its own segment",
    ),
    (
        AGENT_PAYLOAD_BASE, "npm test", 0,
        "a non-git command is out of scope regardless of agent_id",
    ),
]


def check_integration() -> list:
    fails = []
    for extra_payload, command, expect_code, label in INTEGRATION_CASES:
        payload = dict(extra_payload)
        payload["tool_name"] = "Bash"
        payload["tool_input"] = {"command": command}
        proc = run_hook(payload)
        ok = proc.returncode == expect_code
        print(f"[{'PASS' if ok else 'FAIL'}] integration: {label} -> exit={proc.returncode} stderr={proc.stderr.strip()!r}")
        if not ok:
            fails.append(label)

    # PowerShell tool_name is matched the same way as Bash.
    ps_payload = dict(AGENT_PAYLOAD_BASE)
    ps_payload["tool_name"] = "PowerShell"
    ps_payload["tool_input"] = {"command": "git stash push -u"}
    proc = run_hook(ps_payload)
    label = "PowerShell tool_name matched the same as Bash"
    ok = proc.returncode == 2
    print(f"[{'PASS' if ok else 'FAIL'}] integration: {label} -> exit={proc.returncode}")
    if not ok:
        fails.append(label)

    deny_proc = run_hook({
        **AGENT_PAYLOAD_BASE,
        "tool_name": "Bash",
        "tool_input": {"command": "git stash push -u"},
    })
    label = "denial message names the worktree alternative"
    ok = deny_proc.returncode == 2 and "git worktree add" in deny_proc.stderr
    print(f"[{'PASS' if ok else 'FAIL'}] integration: {label} -> stderr={deny_proc.stderr.strip()!r}")
    if not ok:
        fails.append(label)

    return fails


def run() -> int:
    fails = _testlib.run_cases(AGENT_CALL_CASES, check_agent_call) + check_integration()
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
