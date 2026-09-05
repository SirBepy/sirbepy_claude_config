"""Self-test for send-message-stop-guard.py (todo 410).

Run directly: python hooks/test_send_message_stop_guard.py
Drives guard.main() IN-PROCESS (not subprocess): a subprocess would re-import
the module fresh and write its counter to the real hooks/.session-markers/
instead of the monkeypatched temp dir below - confirmed the hard way, an
earlier subprocess-based version of this suite leaked real marker files into
this repo's own tree on every run.
"""

import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "send-message-stop-guard.py"
guard = _testlib.load_module("send_message_stop_guard", _GUARD_PATH)

ZWSP = chr(0x200B)
DAEMON_RELAY = f"{ZWSP}[daemon-meta]{ZWSP}[repo-channel] Hold sign-off until review lands."


def write_transcript(tmpdir: Path, name: str, user_text: str, tool_names: list) -> Path:
    entries = [{"type": "user", "message": {"content": [{"type": "text", "text": user_text}]}}]
    for i, tool_name in enumerate(tool_names):
        tool_use_id = f"toolu_{i}"
        entries.append({
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "id": tool_use_id, "name": tool_name, "input": {}}]},
        })
        entries.append({
            "type": "user",
            "message": {"content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": "ok"}]},
        })
    path = tmpdir / name
    with open(path, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    return path


def run_stop(transcript_path: Path, session_id: str, stop_hook_active: bool = False) -> tuple:
    payload = {
        "transcript_path": str(transcript_path),
        "session_id": session_id,
        "stop_hook_active": stop_hook_active,
    }
    guard.read_payload = lambda: payload
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            guard.main()
            code = 0
        except SystemExit as e:
            code = e.code
    return code, buf.getvalue()


fails = []

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.SESSION_MARKER_DIR = tmpdir / ".session-markers"

    # --- unit: relay detection and tool-suffix helpers ---

    label = "relay tag detected through zero-width envelope chars"
    ok = guard._is_relay_input(DAEMON_RELAY)
    fails += [] if _testlib.report(ok, label) else [label]

    label = "plain dev text is not a relay"
    ok = not guard._is_relay_input("please fix the build")
    fails += [] if _testlib.report(ok, label) else [label]

    label = "tool suffix strips MCP server prefix"
    ok = guard._tool_suffix("mcp__cc_conductor__send_message") == "send_message"
    fails += [] if _testlib.report(ok, label) else [label]

    # --- integration: no Conductor signal at all is left alone ---

    label = "no report_turn_status and no send_message: nothing to enforce, allowed"
    t = write_transcript(tmpdir, "t1.jsonl", "keep building", [])
    code, out = run_stop(t, "sess-none")
    ok = code == 0 and '"decision"' not in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    # --- integration: a single silent Conductor turn passes (quiet turn tolerated) ---

    label = "one silent report_turn_status turn passes"
    t = write_transcript(tmpdir, "t2.jsonl", "keep building", ["mcp__cc_conductor__report_turn_status"])
    code, out = run_stop(t, "sess-a")
    ok = code == 0 and '"decision"' not in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    label = "a second silent turn still passes"
    code, out = run_stop(t, "sess-a")
    ok = code == 0 and '"decision"' not in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    label = "the third consecutive silent turn is blocked"
    code, out = run_stop(t, "sess-a")
    ok = code == 0 and '"decision": "block"' in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    # --- integration: send_message anywhere this turn resets the streak ---

    label = "a turn that calls send_message resets after a prior silent turn"
    t_silent = write_transcript(tmpdir, "t3a.jsonl", "keep building", ["mcp__cc_conductor__report_turn_status"])
    run_stop(t_silent, "sess-b")  # 1 silent turn recorded
    t_sent = write_transcript(
        tmpdir, "t3b.jsonl", "keep building",
        ["mcp__cc_conductor__report_turn_status", "mcp__cc_conductor__send_message"],
    )
    code, out = run_stop(t_sent, "sess-b")
    ok = code == 0 and '"decision"' not in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    label = "the counter is truly reset: two more silent turns after it still pass"
    code, out = run_stop(t_silent, "sess-b")
    ok1 = code == 0 and '"decision"' not in out
    code, out = run_stop(t_silent, "sess-b")
    ok2 = code == 0 and '"decision"' not in out
    ok = ok1 and ok2
    fails += [] if _testlib.report(ok, f"{label} -> ok1={ok1} ok2={ok2}") else [label]

    # --- integration: relay exception (todo 410's own carve-out) ---

    label = "a relay-only turn (report_turn_status only) is exempt, even on the 3rd streak position"
    t_relay = write_transcript(tmpdir, "t4.jsonl", DAEMON_RELAY, ["mcp__cc_conductor__report_turn_status"])
    t_silent2 = write_transcript(tmpdir, "t4b.jsonl", "keep building", ["mcp__cc_conductor__report_turn_status"])
    run_stop(t_silent2, "sess-c")
    run_stop(t_silent2, "sess-c")
    code, out = run_stop(t_relay, "sess-c")
    ok = code == 0 and '"decision"' not in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    label = "the relay turn did not consume the streak: the next silent turn still blocks"
    code, out = run_stop(t_silent2, "sess-c")
    ok = code == 0 and '"decision": "block"' in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    # --- near-miss: relay input that ALSO produced new information must not be exempt ---

    label = "relay input plus a non-safe tool call gets no exemption and still trips the streak"
    t_relay_active = write_transcript(
        tmpdir, "t5.jsonl", DAEMON_RELAY,
        ["Edit", "mcp__cc_conductor__report_turn_status"],
    )
    run_stop(t_relay_active, "sess-d")
    run_stop(t_relay_active, "sess-d")
    code, out = run_stop(t_relay_active, "sess-d")
    ok = code == 0 and '"decision": "block"' in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    # --- stop_hook_active suppresses re-block (infinite-loop guard) ---

    label = "stop_hook_active True always allows, even mid-streak"
    code, out = run_stop(t_silent, "sess-e", stop_hook_active=True)
    ok = code == 0 and '"decision"' not in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    # --- session-id safety: malformed id never tracked, never crashes ---

    label = "a malformed session id fails open instead of writing a bad marker path"
    t_bad = write_transcript(tmpdir, "t6.jsonl", "keep building", ["mcp__cc_conductor__report_turn_status"])
    code, out = run_stop(t_bad, "$CLAUDE_CODE_SESSION_ID")
    ok = code == 0
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]
    label = "no stray marker written for the malformed id"
    ok = not (guard.SESSION_MARKER_DIR / f"{guard.COUNTER_PREFIX}$CLAUDE_CODE_SESSION_ID").exists()
    fails += [] if _testlib.report(ok, label) else [label]

sys.exit(_testlib.summarize(fails, style="count"))
