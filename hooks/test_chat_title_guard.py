"""Self-test for chat-title-guard.py (todo 1253).

Run directly: python hooks/test_chat_title_guard.py
Exits 0 on all-pass, 1 on any failure.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "chat-title-guard.py"
TOOL = "mcp__cc_conductor__report_turn_status"


def tool_use_line(name, tool_input):
    return json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": name, "input": tool_input}]}})


_counter = [0]


def make_transcript(tmp, lines):
    _counter[0] += 1
    path = Path(tmp) / f"session{_counter[0]}.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def run_hook(payload_text):
    return subprocess.run([sys.executable, str(_GUARD_PATH)], input=payload_text, capture_output=True, text=True)


def pre(tool_name, tool_input, transcript_path):
    return json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool_name,
                       "tool_input": tool_input, "transcript_path": transcript_path})


def cases(tmp):
    plain = tool_use_line("Read", {"file_path": "x"})
    untitled = tool_use_line(TOOL, {"status": "done"})
    blank = tool_use_line(TOOL, {"status": "done", "title": "  "})
    titled = tool_use_line(TOOL, {"status": "done", "title": "Supabase setup"})
    return [
        (TOOL, {"status": "done"}, make_transcript(tmp, [plain]), True, "first call, no title, empty transcript -> deny"),
        (TOOL, {"status": "done", "title": " "}, make_transcript(tmp, [plain]), True, "first call, blank title -> deny"),
        (TOOL, {"status": "done", "title": "Hook wiring"}, make_transcript(tmp, [plain]), False, "first call carries a title -> allow"),
        (TOOL, {"status": "done"}, make_transcript(tmp, [titled]), False, "later call without title after a titled one -> allow"),
        (TOOL, {"status": "done"}, make_transcript(tmp, [untitled, blank]), True, "earlier untitled and blank-titled calls do not count -> deny"),
        ("report_turn_status", {"status": "done"}, make_transcript(tmp, [plain]), True, "bare tool name is matched too"),
        ("mcp__cc_conductor__send_message", {"text": "hi"}, make_transcript(tmp, [plain]), False, "other tools are never touched"),
        (TOOL, {"status": "done"}, str(Path(tmp) / "absent.jsonl"), True, "missing transcript, untitled call -> deny (cannot prove a title was set)"),
    ]


def check(case) -> bool:
    tool_name, tool_input, transcript, expect_deny, label = case
    proc = run_hook(pre(tool_name, tool_input, transcript))
    ok = (proc.returncode == 2) == expect_deny and proc.returncode in (0, 2)
    print(f"[{'PASS' if ok else 'FAIL'}] {label} -> exit={proc.returncode}")
    return ok


def check_fail_open(_case) -> bool:
    proc = run_hook("not json")
    ok = proc.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] fails open on garbage stdin -> exit={proc.returncode}")
    return ok


def check_corrupt_transcript(_case) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "bad.jsonl"
        path.write_bytes(b'{"report_turn_status": \xff\xfe broken\n')
        proc = run_hook(pre(TOOL, {"status": "done", "title": "Fine"}, str(path)))
    ok = proc.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] corrupt transcript with a titled call -> exit={proc.returncode}")
    return ok


def run() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        fails = _testlib.run_cases(cases(tmp), check)
    fails += _testlib.run_cases([("garbage",)], check_fail_open)
    fails += _testlib.run_cases([("corrupt",)], check_corrupt_transcript)
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
