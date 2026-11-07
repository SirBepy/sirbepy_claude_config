"""Self-test for deferred-tool-blind-call-guard.py (todo 1252).

Run directly: python hooks/test_deferred_tool_blind_call_guard.py
Exits 0 on all-pass, 1 on any failure.
"""

import json
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "deferred-tool-blind-call-guard.py"
WRITE_DRAFT = "mcp__cc_conductor__write_draft"
SEND = "mcp__cc_conductor__send_message"

_counter = [0]


def assistant_tool_use(name, tool_input):
    return json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": "t1", "name": name, "input": tool_input}]}})


def tool_result_with_refs(names):
    return json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t1",
         "content": [{"type": "tool_reference", "tool_name": n} for n in names]}]}})


def reminder_listing_names():
    # The deferred-tools reminder is plain user text that names every tool and
    # mentions ToolSearch: it must prove nothing.
    return json.dumps({"type": "user", "message": {"content": [
        {"type": "text", "text": f"Use ToolSearch to load: {WRITE_DRAFT}, {SEND}"}]}})


def make_transcript(tmp, lines):
    _counter[0] += 1
    path = Path(tmp) / f"session{_counter[0]}.jsonl"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def pre(tool_name, transcript_path, session_id=None):
    return json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool_name, "tool_input": {},
                       "transcript_path": transcript_path, "session_id": session_id or uuid.uuid4().hex})


def run_hook(text):
    return subprocess.run([sys.executable, str(_GUARD_PATH)], input=text, capture_output=True, text=True)


def cases(tmp):
    search = lambda q: assistant_tool_use("ToolSearch", {"query": q, "max_results": 5})
    return [
        (WRITE_DRAFT, make_transcript(tmp, [assistant_tool_use("Read", {"file_path": "x"})]), True, "blind first call is denied"),
        (WRITE_DRAFT, make_transcript(tmp, [search(f"select:{WRITE_DRAFT}")]), False, "after ToolSearch select of that tool -> allow"),
        (WRITE_DRAFT, make_transcript(tmp, [search(f"select:{SEND},{WRITE_DRAFT}")]), False, "tool inside a comma-separated select -> allow"),
        (WRITE_DRAFT, make_transcript(tmp, [search("select:write_draft")]), False, "short-name select -> allow"),
        (WRITE_DRAFT, make_transcript(tmp, [search(f"select:{SEND}")]), True, "ToolSearch for a different tool does not load this one"),
        (WRITE_DRAFT, make_transcript(tmp, [search("draft")]), True, "keyword query with no tool_reference result proves nothing"),
        (WRITE_DRAFT, make_transcript(tmp, [search("draft"), tool_result_with_refs([WRITE_DRAFT])]), False, "keyword search whose result references the tool -> allow"),
        (WRITE_DRAFT, make_transcript(tmp, [reminder_listing_names()]), True, "plain text listing the tool names proves nothing"),
        (WRITE_DRAFT, make_transcript(tmp, [assistant_tool_use(WRITE_DRAFT, {"action": "create"})]), True, "an earlier denied call to the tool itself is not a load"),
        ("Bash", make_transcript(tmp, []), False, "non-conductor tool is never touched"),
        ("mcp__other__thing", make_transcript(tmp, []), False, "another MCP server is never touched"),
    ]


def check(case) -> bool:
    tool_name, transcript, expect_deny, label = case
    proc = run_hook(pre(tool_name, transcript))
    ok = (proc.returncode == 2) == expect_deny and proc.returncode in (0, 2)
    print(f"[{'PASS' if ok else 'FAIL'}] {label} -> exit={proc.returncode}")
    return ok


def check_cache(_case) -> bool:
    """Once a tool is proven loaded, a later call passes even if the
    transcript can no longer show it (cache hit), and another tool in the
    same session is still gated."""
    with tempfile.TemporaryDirectory() as tmp:
        sid = uuid.uuid4().hex
        first = make_transcript(tmp, [assistant_tool_use("ToolSearch", {"query": f"select:{WRITE_DRAFT}"})])
        empty = make_transcript(tmp, [])
        a = run_hook(pre(WRITE_DRAFT, first, sid)).returncode
        b = run_hook(pre(WRITE_DRAFT, empty, sid)).returncode
        c = run_hook(pre(SEND, empty, sid)).returncode
    ok = (a, b, c) == (0, 0, 2)
    print(f"[{'PASS' if ok else 'FAIL'}] per-session cache: loaded tool stays allowed, a sibling stays gated -> {(a, b, c)}")
    return ok


def check_fail_open(_case) -> bool:
    proc = run_hook("not json")
    ok = proc.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] fails open on garbage stdin -> exit={proc.returncode}")
    return ok


def run() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        fails = _testlib.run_cases(cases(tmp), check)
    fails += _testlib.run_cases([("cache",)], check_cache)
    fails += _testlib.run_cases([("garbage",)], check_fail_open)
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
