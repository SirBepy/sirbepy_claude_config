"""Self-test for agent-todo-write-guard.py (todo 404).

Run directly: python hooks/test_agent_todo_write_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "agent-todo-write-guard.py"
guard = _testlib.load_module("agent_todo_write_guard", _GUARD_PATH)

# (payload agent fields, expected bool, label)
AGENT_CALL_CASES = [
    ({"agent_id": "aaaeae68dcacc2c9d", "agent_type": "general-purpose"}, True, "agent_id + agent_type present -> agent call"),
    ({"agent_id": "aaaeae68dcacc2c9d"}, True, "agent_id present alone is still enough"),
    ({}, False, "neither key present -> orchestrator"),
    ({"agent_id": ""}, False, "empty-string agent_id is falsy, not a real id"),
    ({"agent_type": "general-purpose"}, False, "agent_type alone without agent_id never observed live; not treated as an agent call"),
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


def check_integration() -> list:
    fails = []
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        todos_dir = tmpdir / ".claude" / "todos"
        claims_dir = todos_dir / ".claims"
        done_dir = todos_dir / "done"
        claims_dir.mkdir(parents=True)
        done_dir.mkdir(parents=True)

        backlog_path = todos_dir / "500-new-finding-a-subagent-should-not-file.md"
        backlog_content = "# A new finding a subagent should not file\n\nGoal: report it instead.\n"

        existing_backlog_path = todos_dir / "404-nothing-stops-a-subagent-writing-into-the-todos-backlog.md"

        claim_path = claims_dir / "404.claim"
        heartbeat_content = "session: test\npid: 1\nheartbeat: 1\n"

        done_path = done_dir / "291-old-thing.md"

        agent_payload_base = {"agent_id": "aaaeae68dcacc2c9d", "agent_type": "general-purpose"}
        orchestrator_payload_base = {"session_id": "top-level-session"}

        cases = [
            # (extra payload fields, tool_name, file_path, content_key, content, expect_code, label)
            (
                agent_payload_base, "Write", backlog_path, "content", backlog_content, 2,
                "subagent Write of a NEW backlog .md is denied",
            ),
            (
                orchestrator_payload_base, "Write", backlog_path, "content", backlog_content, 0,
                "orchestrator Write of the same NEW backlog .md is allowed",
            ),
            (
                agent_payload_base, "Edit", existing_backlog_path, "new_string", "updated body", 2,
                "subagent Edit of an EXISTING backlog .md is denied",
            ),
            (
                orchestrator_payload_base, "Edit", existing_backlog_path, "new_string", "updated body", 0,
                "orchestrator Edit of the same EXISTING backlog .md is allowed",
            ),
            (
                agent_payload_base, "Write", claim_path, "content", heartbeat_content, 0,
                "subagent claiming/heartbeating its own .claims/<id>.claim is allowed",
            ),
            (
                agent_payload_base, "Edit", claim_path, "new_string", heartbeat_content, 0,
                "subagent heartbeat Edit of .claims/<id>.claim is allowed",
            ),
            (
                agent_payload_base, "Write", done_path, "content", "# Old thing\n", 0,
                "subagent write targeting done/ is out of this guard's scope",
            ),
            (
                agent_payload_base, "Write", todos_dir / "PLAN.md", "content", "ordered lane\n", 0,
                "subagent write to PLAN.md (no numeric prefix) is out of scope",
            ),
            (
                agent_payload_base, "Bash", backlog_path, "content", backlog_content, 0,
                "non-Write/Edit tool is out of scope regardless of agent_id",
            ),
        ]

        for extra_payload, tool_name, file_path, content_key, content, expect_code, label in cases:
            payload = dict(extra_payload)
            payload["tool_name"] = tool_name
            payload["tool_input"] = {"file_path": str(file_path), content_key: content}
            proc = run_hook(payload)
            ok = proc.returncode == expect_code
            print(f"[{'PASS' if ok else 'FAIL'}] integration: {label} -> exit={proc.returncode} stderr={proc.stderr.strip()!r}")
            if not ok:
                fails.append(label)

        deny_proc = run_hook({
            **agent_payload_base,
            "tool_name": "Write",
            "tool_input": {"file_path": str(backlog_path), "content": backlog_content},
        })
        label = "denial message points the subagent at the Out-of-scope findings report channel"
        ok = deny_proc.returncode == 2 and "Out-of-scope findings" in deny_proc.stderr
        print(f"[{'PASS' if ok else 'FAIL'}] integration: {label} -> stderr={deny_proc.stderr.strip()!r}")
        if not ok:
            fails.append(label)

    return fails


def run() -> int:
    fails = _testlib.run_cases(AGENT_CALL_CASES, check_agent_call) + check_integration()
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
