"""Self-test for schedulewakeup-guard.py.

Run directly: python hooks/test_schedulewakeup_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Confirmed live and wired: settings.json still registers this hook's
PreToolUse command for ScheduleWakeup (checked this session, not assumed).
Covers find_command_names/is_human_authored/last_user_turn_index/
has_pending_background_dispatch against a hand-built transcript, then
drives the real guard.main() with sys.stdin swapped for an in-memory
StringIO and a temp transcript file - no subprocess, no network.
"""

import io
import json
import sys
import tempfile
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "schedulewakeup-guard.py"
)


def jsonl(entries: list) -> str:
    return "\n".join(json.dumps(e) for e in entries)


HUMAN_TEXT = {"type": "user", "message": {"content": "keep going"}}
TOOL_RESULT_ONLY = {
    "type": "user",
    "message": {"content": [{"type": "tool_result", "content": "ok"}]},
}
META_USER = {"type": "user", "isMeta": True, "message": {"content": "system note"}}
ASSISTANT_BG_BASH = {
    "type": "assistant",
    "message": {
        "content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": "x", "run_in_background": True}}
        ]
    },
}
ASSISTANT_FG_BASH = {
    "type": "assistant",
    "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "x"}}]},
}
LOOP_COMMAND = {
    "type": "user",
    "message": {"content": "<command-name>/loop</command-name>\n5m /foo"},
}

# --- is_human_authored ---

fails = []
label = "a plain-string user message is human-authored"
if not _testlib.report(guard.is_human_authored(HUMAN_TEXT) is True, label):
    fails.append(label)

label = "a user turn made only of tool_result blocks is synthetic, not human"
if not _testlib.report(guard.is_human_authored(TOOL_RESULT_ONLY) is False, label):
    fails.append(label)

label = "an isMeta user entry is never treated as human-authored"
if not _testlib.report(guard.is_human_authored(META_USER) is False, label):
    fails.append(label)

label = "an assistant entry is never human-authored"
if not _testlib.report(guard.is_human_authored(ASSISTANT_FG_BASH) is False, label):
    fails.append(label)

# --- find_command_names ---

entries = [HUMAN_TEXT, LOOP_COMMAND]
label = "find_command_names picks up /loop from a command-name block"
if not _testlib.report("loop" in guard.find_command_names(entries), label):
    fails.append(label)

label = "find_command_names finds nothing when no command-name block exists"
if not _testlib.report(guard.find_command_names([HUMAN_TEXT]) == set(), label):
    fails.append(label)

# --- last_user_turn_index ---

entries = [HUMAN_TEXT, ASSISTANT_FG_BASH, TOOL_RESULT_ONLY, ASSISTANT_BG_BASH]
label = "last_user_turn_index anchors on the real human turn, skips the tool-result-only one"
if not _testlib.report(guard.last_user_turn_index(entries) == 0, label):
    fails.append(label)

# --- has_pending_background_dispatch ---

label = "a background Bash tool_use after the turn start is detected"
if not _testlib.report(
    guard.has_pending_background_dispatch([HUMAN_TEXT, ASSISTANT_BG_BASH], 0) is True, label
):
    fails.append(label)

label = "a foreground-only Bash tool_use is not a pending background dispatch"
if not _testlib.report(
    guard.has_pending_background_dispatch([HUMAN_TEXT, ASSISTANT_FG_BASH], 0) is False, label
):
    fails.append(label)

# --- main(): stdin swapped, temp transcript file, restored either way ---


def run_main(payload: dict) -> tuple:
    original_stdin, original_stdout = sys.stdin, sys.stdout
    sys.stdin = io.StringIO(json.dumps(payload))
    sys.stdout = captured = io.StringIO()
    try:
        guard.main()
        code = 0
    except SystemExit as e:
        code = e.code
    finally:
        sys.stdin = original_stdin
        sys.stdout = original_stdout
    return code, captured.getvalue()


with tempfile.TemporaryDirectory() as tmp:
    no_loop_path = Path(tmp) / "no_loop.jsonl"
    no_loop_path.write_text(jsonl([HUMAN_TEXT, ASSISTANT_BG_BASH]), encoding="utf-8")

    loop_path = Path(tmp) / "with_loop.jsonl"
    loop_path.write_text(jsonl([LOOP_COMMAND, ASSISTANT_BG_BASH]), encoding="utf-8")

    fg_only_path = Path(tmp) / "fg_only.jsonl"
    fg_only_path.write_text(jsonl([HUMAN_TEXT, ASSISTANT_FG_BASH]), encoding="utf-8")

    label = "a pending background dispatch with no /loop anywhere is denied"
    code, out = run_main({"transcript_path": str(no_loop_path)})
    if not _testlib.report(code == 2, f"{label} (got exit={code})"):
        fails.append(label)

    label = "any /loop invocation in the transcript allows even with a pending dispatch"
    code, out = run_main({"transcript_path": str(loop_path)})
    if not _testlib.report(code == 0, f"{label} (got exit={code})"):
        fails.append(label)

    label = "no pending background dispatch and no /loop still allows, just warns"
    code, out = run_main({"transcript_path": str(fg_only_path)})
    if not _testlib.report(code == 0, f"{label} (got exit={code})"):
        fails.append(label)

    label = "a missing transcript_path allows silently, never crashes"
    code, out = run_main({})
    if not _testlib.report(code == 0, f"{label} (got exit={code})"):
        fails.append(label)

sys.exit(_testlib.summarize(fails, style="count"))
