"""Self-test for shortcut-raw-write-guard.py.

Run directly: python hooks/test_shortcut_raw_write_guard.py
Exits 0 on all-pass, 1 on any failure. No network: the story fetch and the
env loader are stubbed, and transcripts are temp files.
"""

import json
import tempfile
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "shortcut-raw-write-guard.py"
)

OWNER = "owner-uuid"
STORIES = {
    111: {"requested_by_id": OWNER, "name": "mine"},
    222: {"requested_by_id": "someone-else", "name": "theirs"},
}

guard.load_env_file = lambda path: None
guard.os.environ["SHORTCUT_API_TOKEN"] = "test-token"
guard.os.environ["SHORTCUT_OWNER_UUID"] = OWNER
guard.os.environ.pop(guard.OVERRIDE_ENV, None)


def fake_fetch(story_id, token):
    if story_id not in STORIES:
        raise ValueError("no such story")
    return STORIES[story_id]


guard.fetch_story = fake_fetch

URL = "https://api.app.shortcut.com/api/v3/stories"
fails = []


def write_transcript(tmpdir: Path, name: str, user_texts: list) -> Path:
    path = tmpdir / name
    lines = [json.dumps({"type": "user", "message": {"content": t}}) for t in user_texts]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(tool_name: str, command: str, transcript: Path | None) -> int:
    payload = {"tool_name": tool_name, "tool_input": {"command": command}}
    if transcript:
        payload["transcript_path"] = str(transcript)
    guard.read_payload = lambda: payload
    try:
        guard.main()
        return 0
    except SystemExit as e:
        return e.code


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    plain = write_transcript(tmpdir, "plain.jsonl", ["move my ticket to testing"])
    named = write_transcript(tmpdir, "named.jsonl", ["please move sc-222 to testing too"])
    backfill = write_transcript(tmpdir, "backfill.jsonl", ["/zirtue-release-backfill 3.4.0"])
    audit = write_transcript(tmpdir, "audit.jsonl", ["/shortcut-done-audit sc-222"])
    audit_cmd = write_transcript(
        tmpdir, "audit-cmd.jsonl",
        ["<command-message>shortcut-done-audit</command-message>\n<command-name>/shortcut-done-audit</command-name>"],
    )
    # The skill name merely mentioned in prose, or quoted from a ticket, is not an invocation.
    mention = write_transcript(tmpdir, "mention.jsonl", ["last week I ran /shortcut-done-audit and it was fine"])
    quoted = write_transcript(tmpdir, "quoted.jsonl", ["the ticket says: do not use /zirtue-release-backfill here"])
    skill_call = tmpdir / "skill-call.jsonl"
    skill_call.write_text("\n".join(json.dumps(e) for e in (
        {"type": "user", "message": {"content": "close out the shipped tickets"}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": "t1", "name": "Skill", "input": {"skill": "zirtue-release-backfill"}},
        ]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": "t1", "content": "Launching skill", "is_error": False},
        ]}},
    )) + "\n", encoding="utf-8")

    def skill_transcript(name: str, entries: list) -> Path:
        path = tmpdir / name
        path.write_text("\n".join(json.dumps(e) for e in (
            {"type": "user", "message": {"content": "close out the shipped tickets"}},
            *entries,
        )) + "\n", encoding="utf-8")
        return path

    def skill_use(call_id: str, skill: str = "zirtue-release-backfill") -> dict:
        return {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": call_id, "name": "Skill", "input": {"skill": skill}},
        ]}}

    def skill_result(call_id: str, is_error: bool) -> dict:
        return {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": call_id, "content": "x", "is_error": is_error},
        ]}}

    # Review finding 2026-11-07: a model-issued Skill call to a disable-model-invocation
    # skill errors, and the errored call used to lift the requester and ceiling rules.
    skill_errored = skill_transcript("skill-errored.jsonl", [skill_use("e1"), skill_result("e1", True)])
    skill_no_result = skill_transcript("skill-no-result.jsonl", [skill_use("n1")])
    skill_other_result = skill_transcript("skill-other.jsonl", [skill_use("o1"), skill_result("zzz", False)])
    skill_ok_after_error = skill_transcript(
        "skill-retry.jsonl", [skill_use("r1"), skill_result("r1", True), skill_use("r2"), skill_result("r2", False)],
    )
    skill_plugin_ok = skill_transcript(
        "skill-plugin.jsonl", [skill_use("p1", "plugin:shortcut-done-audit"), skill_result("p1", False)],
    )

    CASES = [
        ("Bash", f'curl -s -X PUT "{URL}/111" -d \'{{"workflow_state_id":500018257}}\'', plain, 0,
         "own story moved to Testing passes"),
        ("Bash", f'curl -s -X PUT "{URL}/222" -d \'{{"workflow_state_id":500018257}}\'', plain, 2,
         "another requester's story is denied"),
        ("Bash", f'curl -s -X PUT "{URL}/222" -d \'{{"workflow_state_id":500018257}}\'', named, 0,
         "another requester's story passes when Joe named it this session"),
        ("Bash", f'curl -s -X PUT "{URL}/111" -d \'{{"workflow_state_id":500018258}}\'', plain, 2,
         "a by-hand PUT to Complete is denied even on an own story"),
        ("Bash", f'curl -s -X PUT "{URL}/222" -d \'{{"workflow_state_id":500018659}}\'', named, 2,
         "naming a ticket does not lift the Testing ceiling"),
        ("Bash", f'curl -s -X PUT "{URL}/222" -d \'{{"workflow_state_id":500018258}}\'', backfill, 0,
         "a /zirtue-release-backfill session may close and touch others' stories"),
        ("Bash", f'curl -s -X PUT "{URL}/222" -d \'{{"workflow_state_id":500018257}}\'', audit, 0,
         "a typed /shortcut-done-audit session may touch others' stories"),
        ("Bash", f'curl -s -X PUT "{URL}/222" -d \'{{"workflow_state_id":500018257}}\'', audit_cmd, 0,
         "a /shortcut-done-audit command block counts as invoked"),
        ("Bash", f'curl -s -X PUT "{URL}/222" -d \'{{"workflow_state_id":500018257}}\'', skill_call, 0,
         "a Skill tool call for zirtue-release-backfill counts as invoked"),
        ("Bash", f'curl -s -X PUT "{URL}/222" -d \'{{"workflow_state_id":500018257}}\'', skill_errored, 2,
         "an errored Skill tool call does not lift the requester rule"),
        ("Bash", f'curl -s -X PUT "{URL}/111" -d \'{{"workflow_state_id":500018258}}\'', skill_errored, 2,
         "an errored Skill tool call does not lift the Testing ceiling"),
        ("Bash", f'curl -s -X PUT "{URL}/222" -d \'{{"workflow_state_id":500018257}}\'', skill_no_result, 2,
         "a Skill tool call with no result yet does not lift the rules"),
        ("Bash", f'curl -s -X PUT "{URL}/222" -d \'{{"workflow_state_id":500018257}}\'', skill_other_result, 2,
         "a success result for a different tool call does not count"),
        ("Bash", f'curl -s -X PUT "{URL}/222" -d \'{{"workflow_state_id":500018257}}\'', skill_ok_after_error, 0,
         "a Skill call that succeeded on retry counts"),
        ("Bash", f'curl -s -X PUT "{URL}/222" -d \'{{"workflow_state_id":500018257}}\'', skill_plugin_ok, 0,
         "a plugin-prefixed Skill name that succeeded counts"),
        ("Bash", f'curl -s -X PUT "{URL}/222" -d \'{{"workflow_state_id":500018257}}\'', mention, 2,
         "mentioning /shortcut-done-audit in prose is not an invocation"),
        ("Bash", f'curl -s -X PUT "{URL}/222" -d \'{{"workflow_state_id":500018258}}\'', quoted, 2,
         "a skill name quoted from a ticket does not lift the ceiling or the requester rule"),
        ("PowerShell", f'Invoke-RestMethod -Uri "{URL}/222" -Method Put -Body $b', plain, 2,
         "Invoke-RestMethod -Method Put is a write"),
        ("Bash", f'curl -s -X POST "{URL}/222/comments" -d \'{{"text":"x"}}\'', plain, 2,
         "a comment on another requester's story is a write too"),
        ("Bash", f'curl -s "{URL}/222" -H "Shortcut-Token: $TOKEN"', plain, 0,
         "a GET of any story passes"),
        ("Bash", f'curl -s -X POST "{URL}" -d \'{{"name":"new"}}\'', plain, 0,
         "story creation is left to shortcut-create-guard"),
        ("Bash", f'curl -s -X PUT "{URL}/999" -d \'{{"name":"x"}}\'', plain, 2,
         "an unverifiable story fails closed"),
        ("Bash", "git commit -m 'curl -X PUT api.app.shortcut.com/api/v3/stories/222'", plain, 0,
         "a Shortcut URL quoted in a commit message is not a write"),
        ("Edit", f'curl -X PUT "{URL}/222"', plain, 0, "non-shell tools are out of scope"),
        ("Bash", f'curl -s "{URL}/222" -d \'name=x\' ; curl -s "{URL}/111" -G', plain, 2,
         "a -G on a different chained curl does not hide a data write to another requester's story"),
        ("Bash", f'curl -s "{URL}/222" ; curl -s -X PUT "{URL}/111" -d \'{{}}\'', plain, 0,
         "a GET chained before an own-story PUT is not treated as a write"),
    ]

    for tool, command, transcript, expected, label in CASES:
        got = run(tool, command, transcript)
        ok = got == expected
        fails += [] if _testlib.report(ok, f"{label} (expected {expected}, got {got})") else [label]

raise SystemExit(_testlib.summarize(fails))
