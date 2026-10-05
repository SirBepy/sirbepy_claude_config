"""Self-test for question-card-live-agent-warn.py (todo 998).

Run directly: python hooks/test_question_card_live_agent_warn.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "question-card-live-agent-warn.py"
guard = _testlib.load_module("question_card_live_agent_warn", _GUARD_PATH)

DISPATCH_BLOCK = {
    "type": "tool_use", "name": "Agent", "id": "toolu_1",
    "input": {"description": "scout", "model": "sonnet", "run_in_background": True},
}
FOREGROUND_BLOCK = {
    "type": "tool_use", "name": "Agent", "id": "toolu_2",
    "input": {"description": "scout", "model": "sonnet", "run_in_background": False},
}
HANDBACK_ENTRY = {
    "type": "user", "isMeta": True,
    "message": {"content": (
        'Another Claude session sent a message:\n<agent-message from="a9faa2941ba516b8d">\n'
        "[Subagent hand-back] The text below is the final report..."
    )},
}
HANDBACK_LIST_ENTRY = {
    "type": "user", "isMeta": True,
    "message": {"content": [{"type": "text", "text": "[Subagent hand-back] final report in a list-shaped entry"}]},
}
PEER_RELAY_ENTRY = {
    "type": "user", "isMeta": True,
    "message": {"content": "​[daemon-meta]​ 1 new peer message. Call read_messages to view."},
}

# --- unit cases for the two predicates ---

BACKGROUND_CASES = [
    (DISPATCH_BLOCK, True, "Agent dispatch with run_in_background:true is a live candidate"),
    (FOREGROUND_BLOCK, False, "Agent dispatch with run_in_background:false is synchronous, not counted"),
    ({"type": "tool_use", "name": "Agent", "input": {}}, True, "run_in_background absent defaults to background per Agent tool docs"),
    ({"type": "tool_use", "name": "Bash", "input": {"run_in_background": True}}, False, "Bash is not a dispatch tool"),
    ({"type": "text", "text": "hi"}, False, "a non tool_use block is never a dispatch"),
]

HANDBACK_CASES = [
    (HANDBACK_ENTRY, True, "string-content hand-back entry recognized"),
    (HANDBACK_LIST_ENTRY, True, "list-content hand-back entry recognized"),
    (PEER_RELAY_ENTRY, False, "an ordinary peer-relay isMeta entry is not a hand-back"),
    ({"type": "user", "isMeta": False, "message": {"content": "[Subagent hand-back] x"}}, False, "non-meta entry never counts even with the marker text"),
    ({"type": "assistant", "isMeta": True, "message": {"content": "[Subagent hand-back] x"}}, False, "wrong entry type never counts"),
]


def check_background(case) -> bool:
    block, expected, label = case
    got = guard.is_background_dispatch(block)
    ok = got == expected
    print(f"[{'PASS' if ok else 'FAIL'}] is_background_dispatch: {label} -> {got}")
    return ok


def check_handback(case) -> bool:
    entry, expected, label = case
    got = guard.is_handback_notice(entry)
    ok = got == expected
    print(f"[{'PASS' if ok else 'FAIL'}] is_handback_notice: {label} -> {got}")
    return ok


def _assistant_entry(*blocks) -> dict:
    return {"type": "assistant", "message": {"content": list(blocks)}}


# (entries, expected_count, label)
COUNT_CASES = [
    ([], 0, "empty transcript -> 0"),
    ([_assistant_entry(DISPATCH_BLOCK)], 1, "one live dispatch, no hand-back yet -> 1"),
    ([_assistant_entry(DISPATCH_BLOCK), HANDBACK_ENTRY], 0, "dispatch then its hand-back -> 0"),
    (
        [_assistant_entry(DISPATCH_BLOCK, DISPATCH_BLOCK), HANDBACK_ENTRY],
        1,
        "two dispatches, one hand-back -> 1 still live",
    ),
    (
        [_assistant_entry(DISPATCH_BLOCK), HANDBACK_ENTRY, HANDBACK_ENTRY],
        0,
        "more hand-backs than dispatches floors at 0, never negative",
    ),
    (
        [_assistant_entry(FOREGROUND_BLOCK)],
        0,
        "a synchronous dispatch never contributes to the live count",
    ),
]


def check_count(case) -> bool:
    entries, expected, label = case
    got = guard.live_agent_count(entries)
    ok = got == expected
    print(f"[{'PASS' if ok else 'FAIL'}] live_agent_count: {label} -> {got}")
    return ok


def run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_GUARD_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def write_transcript(tmpdir: Path, entries: list) -> Path:
    path = tmpdir / "transcript.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return path


def check_integration() -> list:
    fails = []
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)

        live_path = write_transcript(tmpdir, [_assistant_entry(DISPATCH_BLOCK)])
        proc = run_hook({"transcript_path": str(live_path), "tool_name": "AskUserQuestion", "tool_input": {}})
        label = "a live dispatch with no hand-back produces an allow-with-warning, not a block"
        ok = proc.returncode == 0 and "question-card-live-agent-warn" in proc.stdout and '"permissionDecision": "allow"' in proc.stdout
        print(f"[{'PASS' if ok else 'FAIL'}] integration: {label} -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not ok:
            fails.append(label)

        resolved_path = write_transcript(tmpdir, [_assistant_entry(DISPATCH_BLOCK), HANDBACK_ENTRY])
        proc = run_hook({"transcript_path": str(resolved_path), "tool_name": "AskUserQuestion", "tool_input": {}})
        label = "a dispatch already handed back produces no warning"
        ok = proc.returncode == 0 and proc.stdout.strip() == ""
        print(f"[{'PASS' if ok else 'FAIL'}] integration: {label} -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not ok:
            fails.append(label)

        missing_path = tmpdir / "does-not-exist.jsonl"
        proc = run_hook({"transcript_path": str(missing_path), "tool_name": "AskUserQuestion", "tool_input": {}})
        label = "a missing transcript_path fails open with no warning"
        ok = proc.returncode == 0 and proc.stdout.strip() == ""
        print(f"[{'PASS' if ok else 'FAIL'}] integration: {label} -> exit={proc.returncode}")
        if not ok:
            fails.append(label)

    return fails


def run() -> int:
    fails = (
        _testlib.run_cases(BACKGROUND_CASES, check_background)
        + _testlib.run_cases(HANDBACK_CASES, check_handback)
        + _testlib.run_cases(COUNT_CASES, check_count)
        + check_integration()
    )
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
