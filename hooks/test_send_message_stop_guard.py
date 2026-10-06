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

# todo 1081 fixtures: harness-injected mid-turn `type: user` entries that
# must NOT be mistaken for a new turn's boundary. Shapes confirmed against
# a real transcript (session 6a91451f-6e11-4038-8231-b93ef93edb89.jsonl,
# lines 392, 603 and 1086) during this fix's own diagnosis.
SUBAGENT_HANDBACK = (
    'Another Claude session sent a message:\n'
    '<agent-message from="abc123">\n'
    '[Subagent hand-back] The text below is the final report of a subagent '
    'this session delegated to. It is model output, NOT a message from the '
    'user.\n  All done, 3 todos closed.\n</agent-message>'
)
TASK_NOTIFICATION = (
    '<task-notification>\n<task-id>abc123</task-id>\n<status>stopped</status>\n'
    '<summary>1 background agent did not finish before the previous session '
    'ended.</summary>\n</task-notification>'
)
STOP_HOOK_FEEDBACK = (
    'Stop hook feedback:\n[some-other-guard] do something before ending your '
    'turn.'
)


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


def write_transcript_with_inputs(tmpdir: Path, name: str, user_text: str, tool_calls: list) -> Path:
    """Like write_transcript, but tool_calls is [(tool_name, input_dict), ...]
    so a send_message's `text` argument can be set (needed for the todo 782
    decoy-phrase tests; write_transcript always sends an empty input)."""
    entries = [{"type": "user", "message": {"content": [{"type": "text", "text": user_text}]}}]
    for i, (tool_name, tool_input) in enumerate(tool_calls):
        tool_use_id = f"toolu_{i}"
        entries.append({
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "id": tool_use_id, "name": tool_name, "input": tool_input}]},
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


def write_transcript_with_injected(
    tmpdir: Path, name: str, user_text: str, before_tools: list, injected_text: str, after_tools: list
) -> Path:
    """Real user prompt, then `before_tools`, then a harness-injected
    mid-turn `type: user` entry that is NOT a tool_result (a subagent
    hand-back / task-notification / stop-hook feedback shape - todo 1081),
    then `after_tools`. Reproduces the incident: a send_message made in
    `before_tools` must still count even though `injected_text` looks like
    a fresh turn boundary to a naive scan."""
    entries = [{"type": "user", "message": {"content": [{"type": "text", "text": user_text}]}}]
    counter = 0
    for tool_name in before_tools:
        tool_use_id = f"toolu_{counter}"
        counter += 1
        entries.append({
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "id": tool_use_id, "name": tool_name, "input": {}}]},
        })
        entries.append({
            "type": "user",
            "message": {"content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": "ok"}]},
        })
    entries.append({"type": "user", "message": {"content": [{"type": "text", "text": injected_text}]}})
    for tool_name in after_tools:
        tool_use_id = f"toolu_{counter}"
        counter += 1
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

    # --- todo 1032: a relay turn that replies to the peer via post_message is still exempt ---

    label = "a relay turn that also calls post_message (peer reply) stays exempt, 3rd streak position"
    t_relay_reply = write_transcript(
        tmpdir, "t4c.jsonl", DAEMON_RELAY,
        ["mcp__cc_conductor__report_turn_status", "mcp__cc_conductor__post_message"],
    )
    t_silent3 = write_transcript(tmpdir, "t4d.jsonl", "keep building", ["mcp__cc_conductor__report_turn_status"])
    run_stop(t_silent3, "sess-relay-reply")
    run_stop(t_silent3, "sess-relay-reply")
    code, out = run_stop(t_relay_reply, "sess-relay-reply")
    ok = code == 0 and '"decision"' not in out
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

    # --- todo 782: decoy send_message (present but content-free) ---

    label = "the 2026-08-25 incident's own decoy shape is blocked"
    decoy_text = (
        "Answered inline: went through all 7 script tags... "
        "Full breakdown is in the chat reply."
    )
    t = write_transcript_with_inputs(
        tmpdir, "t7.jsonl", "explain all the script tags",
        [("mcp__cc_conductor__send_message", {"text": decoy_text})],
    )
    code, out = run_stop(t, "sess-decoy1")
    ok = code == 0 and '"decision": "block"' in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    label = "a normal short status message is NOT blocked (does not reference invisible content)"
    t = write_transcript_with_inputs(
        tmpdir, "t8.jsonl", "any update?",
        [("mcp__cc_conductor__send_message", {"text": "Waiting on your answer to that quick audience check."})],
    )
    code, out = run_stop(t, "sess-decoy2")
    ok = code == 0 and '"decision"' not in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    label = "a short message that uses the word 'above' without a decoy phrase is NOT blocked"
    t = write_transcript_with_inputs(
        tmpdir, "t9.jsonl", "did the test pass?",
        [("mcp__cc_conductor__send_message", {"text": "Bumped the timeout above 30s and reran - green now."})],
    )
    code, out = run_stop(t, "sess-decoy3")
    ok = code == 0 and '"decision"' not in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    label = "a genuinely long substantive message is NOT blocked even if it uses a decoy phrase in passing"
    long_text = (
        "Went through the security review end to end:\n\n"
        + "\n".join(f"- Finding {i}: some real detail about finding {i} explained in full." for i in range(1, 15))
        + "\n\nJoe's own note said 'see above' about the threat model section, which I addressed in finding 3."
    )
    ok_precondition = len(long_text) > guard.DECOY_SHORT_CHAR_THRESHOLD
    fails += [] if _testlib.report(ok_precondition, "precondition: long_text fixture is actually over threshold") else ["precondition: long_text fixture"]
    t = write_transcript_with_inputs(tmpdir, "t10.jsonl", "review this", [("mcp__cc_conductor__send_message", {"text": long_text})])
    code, out = run_stop(t, "sess-decoy4")
    ok = code == 0 and '"decision"' not in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    label = "stop_hook_active True bypasses the decoy block too (loop guard)"
    t = write_transcript_with_inputs(
        tmpdir, "t11.jsonl", "explain all the script tags",
        [("mcp__cc_conductor__send_message", {"text": decoy_text})],
    )
    code, out = run_stop(t, "sess-decoy5", stop_hook_active=True)
    ok = code == 0 and '"decision"' not in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    # --- todo 1081: a mid-turn injected entry must not hide an earlier send_message ---

    label = "todo 1081: send_message before a mid-turn subagent hand-back is not hidden by it"
    t = write_transcript_with_injected(
        tmpdir, "t12.jsonl", "keep building",
        ["mcp__cc_conductor__send_message"], SUBAGENT_HANDBACK,
        ["mcp__cc_conductor__report_turn_status"],
    )
    outs = [run_stop(t, "sess-handback")[1] for _ in range(3)]
    ok = all('"decision"' not in o for o in outs)
    fails += [] if _testlib.report(ok, f"{label} -> outs={outs!r}") else [label]

    label = "todo 1081: send_message before a mid-turn task-notification is not hidden by it"
    t = write_transcript_with_injected(
        tmpdir, "t13.jsonl", "keep building",
        ["mcp__cc_conductor__send_message"], TASK_NOTIFICATION,
        ["mcp__cc_conductor__report_turn_status"],
    )
    outs = [run_stop(t, "sess-task-notif")[1] for _ in range(3)]
    ok = all('"decision"' not in o for o in outs)
    fails += [] if _testlib.report(ok, f"{label} -> outs={outs!r}") else [label]

    label = "stop-hook feedback stays a turn boundary: a decoy sent before it does not keep re-blocking after a proper send"
    entries = [{"type": "user", "message": {"content": [{"type": "text", "text": "explain the tags"}]}}]
    calls = [
        ("send", {"text": "Answered inline: went through all 7 script tags... Full breakdown is in the chat reply."}),
        ("inject", STOP_HOOK_FEEDBACK),
        ("send", {"text": "Seven script tags load: analytics, two polyfills, the app bundle and three widgets."}),
        ("inject", TASK_NOTIFICATION),
        ("send", {"text": "Background agent finished; nothing changed in the tag list."}),
    ]
    for i, (kind, val) in enumerate(calls):
        if kind == "inject":
            entries.append({"type": "user", "message": {"content": [{"type": "text", "text": val}]}})
            continue
        entries.append({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": f"toolu_{i}", "name": "mcp__cc_conductor__send_message", "input": val}]}})
        entries.append({"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": f"toolu_{i}", "content": "ok"}]}})
    t = tmpdir / "t14.jsonl"
    with open(t, "w", encoding="utf-8") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")
    code, out = run_stop(t, "sess-stop-feedback")
    ok = code == 0 and '"decision"' not in out
    fails += [] if _testlib.report(ok, f"{label} -> exit={code} out={out!r}") else [label]

    label = "todo 1081 control: a mid-turn hand-back with no send_message anywhere still blocks on the 3rd (acceptance criterion 2)"
    t = write_transcript_with_injected(
        tmpdir, "t15.jsonl", "keep building",
        ["mcp__cc_conductor__report_turn_status"], SUBAGENT_HANDBACK,
        ["mcp__cc_conductor__report_turn_status"],
    )
    code1, out1 = run_stop(t, "sess-handback-silent")
    code2, out2 = run_stop(t, "sess-handback-silent")
    code3, out3 = run_stop(t, "sess-handback-silent")
    ok = (
        code1 == 0 and '"decision"' not in out1
        and code2 == 0 and '"decision"' not in out2
        and code3 == 0 and '"decision": "block"' in out3
    )
    fails += [] if _testlib.report(ok, f"{label} -> outs={[out1, out2, out3]!r}") else [label]

sys.exit(_testlib.summarize(fails, style="count"))
