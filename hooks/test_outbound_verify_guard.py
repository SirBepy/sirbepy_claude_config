"""Self-test for outbound-verify-guard.py.

Run directly: python hooks/test_outbound_verify_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Two halves: detection (which calls are outbound prose at all, and what text they send), and
the transcript tally (whether 3 independent PASS verdicts cover that exact text). Every
end-to-end case runs the real script on a synthetic transcript written to a temp dir, in the
three delivery shapes the harness actually uses (checked against live transcripts
2026-10-05): the report inline in the tool_result, an async `<agent-message>` hand-back, and
a sync hand-back enqueued BEFORE the tool_result that names its agentId.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

HOOK = Path(__file__).resolve().parent / "outbound-verify-guard.py"
guard = _testlib.load_module("guard", HOOK)

SC = "https://api.app.shortcut.com/api/v3/stories"
LIN = "https://api.linear.app/graphql"
CLAIM = "The biller address field in CreateLoan.tsx skips validation when the country is empty."
OTHER = "Totally different claim about the payments service retry loop and its backoff."
TITLE = "Validate biller address on the CreateLoan screen"

# (tool_name, tool_input, expect_detected, label)
DETECT_CASES = [
    ("Bash", {"command": f"curl -X POST {SC} -d '{{\"name\": \"{TITLE}\", \"description\": \"{CLAIM}\"}}'"}, True, "Shortcut REST create"),
    ("Bash", {"command": f"curl -X POST {SC}/123/comments -d '{{\"text\": \"{CLAIM}\"}}'"}, True, "Shortcut REST comment"),
    ("Bash", {"command": f"curl -X PUT {SC}/123 -d '{{\"description\": \"{CLAIM}\"}}'"}, True, "Shortcut REST description rewrite"),
    ("Bash", {"command": f"curl -X PUT {SC}/123 -d '{{\"workflow_state_id\": 500000011}}'"}, False, "Shortcut state move stays ungated"),
    ("Bash", {"command": f"curl -G {SC}/search -d query=biller"}, False, "Shortcut search read"),
    ("PowerShell", {"command": f"$b = @{{ text = \"{CLAIM}\" }} | ConvertTo-Json; Invoke-RestMethod -Uri {SC}/9/comments -Method Post -Body $b"}, True, "PowerShell hashtable comment"),
    ("Bash", {"command": f"curl -X POST {LIN} -d '{{\"query\": \"mutation($i: IssueCreateInput!) {{ issue" "Create(input: $i) {{ success }} }}\", \"variables\": {{\"i\": {{\"title\": \"{TITLE}\", \"description\": \"{CLAIM}\"}}}}}}'"}, True, "Linear GraphQL create via variables"),
    ("Bash", {"command": f"curl -X POST {LIN} -d '{{\"query\": \"mutation {{ issue" "Update(id: \\\"x\\\", input: {{stateId: \\\"s\\\"}}) {{ success }} }}\"}}'"}, False, "Linear state move stays ungated"),
    ("Bash", {"command": f"gh pr create --title \"{TITLE}\" --body \"{CLAIM}\""}, True, "gh pr create"),
    ("Bash", {"command": f"gh pr comment 12 -b \"{CLAIM}\""}, True, "gh pr comment"),
    ("Bash", {"command": f"gh pr review 12 --approve --body \"{CLAIM}\""}, True, "gh pr review with a body"),
    ("Bash", {"command": "gh pr review 12 --approve"}, False, "bare approve says nothing"),
    ("Bash", {"command": "gh pr edit 12 --add-label bug"}, False, "label edit says nothing"),
    ("Bash", {"command": "gh pr view 12 --json body"}, False, "gh pr view is a read"),
    ("Bash", {"command": f"gh api repos/o/r/issues/12/comments -f body=\"{CLAIM}\""}, True, "gh api PR conversation comment"),
    ("Bash", {"command": f"gh api repos/o/r/pulls/12/reviews -f body=\"{CLAIM}\" -f event=COMMENT"}, True, "gh api review"),
    ("Bash", {"command": "gh api repos/o/r/pulls/12/comments"}, False, "gh api GET is a read"),
    ("Bash", {"command": "gh api -X PUT repos/o/r/pulls/12/merge"}, False, "merge carries no prose"),
    ("mcp__shortcut__stories-create-comment", {"storyPublicId": 1, "text": CLAIM}, True, "Shortcut MCP comment"),
    ("mcp__shortcut__stories-update", {"storyPublicId": 1, "workflow_state_id": 5}, False, "Shortcut MCP state move"),
    ("mcp__claude_ai_Linear__create_comment", {"issueId": "x", "body": CLAIM}, True, "Linear MCP comment"),
    ("mcp__github__add_issue_comment", {"owner": "o", "repo": "r", "issue_number": 1, "body": CLAIM}, True, "GitHub MCP comment"),
    ("mcp__github__get_pull_request", {"owner": "o", "repo": "r", "pullNumber": 1}, False, "GitHub MCP read"),
    ("Bash", {"command": "git commit -m 'FEAT: post a comment to shortcut'"}, False, "unrelated command"),
    ("Read", {"file_path": "x"}, False, "non-shell tool"),
]


def check_detect(case) -> bool:
    tool_name, tool_input, expect, label = case
    got = guard.detect(tool_name, tool_input, None) is not None
    return _testlib.report(got == expect, f"detect: {label} (got {got})")


def draft_prompt(text: str) -> str:
    return (
        "READ-ONLY DISPATCH\nVerify every claim.\n<<<OUTBOUND-DRAFT\n"
        + text
        + "\nOUTBOUND-DRAFT>>>\nEnd with OUTBOUND-VERDICT: PASS or OUTBOUND-VERDICT: FAIL on its own line.\n"
    )


def dispatch(n: int, text: str, subagent_type: str = "general-purpose") -> dict:
    return {
        "type": "assistant",
        "message": {"content": [{
            "type": "tool_use", "id": f"toolu_{n}", "name": "Agent",
            "input": {"prompt": draft_prompt(text), "model": "sonnet", "subagent_type": subagent_type},
        }]},
    }


def inline_result(n: int, verdict: str) -> dict:
    return {
        "type": "user",
        "toolUseResult": {"status": "completed", "agentId": f"a{n}"},
        "message": {"content": [{
            "type": "tool_result", "tool_use_id": f"toolu_{n}",
            "content": [{"type": "text", "text": f"Claim 1: CONFIRMED.\nOUTBOUND-VERDICT: {verdict}"}],
        }]},
    }


def launched_result(n: int) -> dict:
    return {
        "type": "user",
        "toolUseResult": {"isAsync": True, "status": "async_launched", "agentId": f"a{n}"},
        "message": {"content": [{
            "type": "tool_result", "tool_use_id": f"toolu_{n}",
            "content": [{"type": "text", "text": "Async agent launched successfully."}],
        }]},
    }


def handback(n: int, verdict: str) -> dict:
    body = f'<agent-message from="a{n}">\n[Subagent hand-back] The report follows:\n  Claim 1: checked.\n  OUTBOUND-VERDICT: {verdict}\n</agent-message>'
    return {"type": "attachment", "attachment": {"type": "queued_command", "prompt": body}}


def queued(n: int, verdict: str) -> dict:
    body = f'<agent-message from="a{n}">\n  OUTBOUND-VERDICT: {verdict}\n</agent-message>'
    return {"type": "queue-operation", "operation": "enqueue", "content": body}


def three_inline(text: str, verdicts=("PASS", "PASS", "PASS"), start: int = 1) -> list:
    out = []
    for i, v in enumerate(verdicts, start):
        out += [dispatch(i, text), inline_result(i, v)]
    return out


def run_hook(tool_input: dict, entries: list | None, env_extra: dict | None = None, tool_name: str = "Bash") -> int:
    with tempfile.TemporaryDirectory() as tmp:
        payload = {"tool_name": tool_name, "tool_input": tool_input, "cwd": tmp}
        if entries is not None:
            transcript = Path(tmp) / "t.jsonl"
            transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
            payload["transcript_path"] = str(transcript)
        env = {k: v for k, v in os.environ.items() if k != guard.OVERRIDE_ENV}
        env.update(env_extra or {})
        proc = subprocess.run(
            [sys.executable, str(HOOK)], input=json.dumps(payload), capture_output=True,
            text=True, encoding="utf-8", env=env, timeout=30,
        )
        return proc.returncode


COMMENT = {"command": f"gh pr comment 12 --body \"{CLAIM}\""}
BATCH = {"command": f"gh pr create --title \"{TITLE}\" --body \"{CLAIM}\""}

# (tool_input, transcript entries or None, env, expected exit code, label)
E2E_CASES = [
    (COMMENT, [], None, 2, "no verifiers at all blocks"),
    (COMMENT, three_inline(CLAIM), None, 0, "3 inline PASS clears"),
    (COMMENT, three_inline(CLAIM, ("PASS", "PASS")), None, 2, "2 PASS is not enough"),
    (COMMENT, three_inline(CLAIM, ("PASS", "PASS", "FAIL")), None, 2, "one FAIL blocks (unanimous)"),
    (COMMENT, three_inline(CLAIM, ("PASS", "PASS", "FAIL", "PASS")), None, 2, "re-rolling past a FAIL never clears that text"),
    (
        {"command": f"gh pr comment 12 --body \"{CLAIM.replace('skips', 'skip')}\""},
        three_inline(CLAIM), None, 2, "an edit after verification needs a new round",
    ),
    (
        {"command": f"gh pr comment 12 --body \"{CLAIM}\""},
        three_inline(f"{OTHER}\n\n{CLAIM}"), None, 0, "one verified draft can hold a batch of comments",
    ),
    (COMMENT, three_inline("  " + CLAIM.replace(" ", "\n  ", 3) + "  "), None, 0, "whitespace differences are ignored"),
    (COMMENT, three_inline(OTHER), None, 2, "verifying different text does not count"),
    (
        COMMENT,
        [dispatch(i, CLAIM, "fork") for i in (1, 2, 3)] + [inline_result(i, "PASS") for i in (1, 2, 3)],
        None, 2, "fork dispatches are not independent",
    ),
    (
        COMMENT,
        sum(([dispatch(i, CLAIM), launched_result(i)] for i in (1, 2, 3)), []) + [handback(i, "PASS") for i in (1, 2, 3)],
        None, 0, "async hand-backs clear",
    ),
    (
        COMMENT,
        sum(([dispatch(i, CLAIM), queued(i, "PASS"), launched_result(i)] for i in (1, 2, 3)), []),
        None, 0, "sync hand-back enqueued before its tool_result clears",
    ),
    (
        COMMENT,
        sum(([dispatch(i, CLAIM), launched_result(i)] for i in (1, 2, 3)), []) + [handback(1, "PASS"), handback(2, "PASS"), handback(3, "FAIL"), handback(3, "PASS")],
        None, 0, "a resumed verifier's latest report wins",
    ),
    (BATCH, three_inline(f"Title: {TITLE}\n\nBody:\n{CLAIM}"), None, 0, "one draft covers title and body"),
    (BATCH, three_inline(CLAIM), None, 2, "an unverified long title blocks"),
    ({"command": f"gh pr create --title \"WIP\" --body \"{CLAIM}\""}, three_inline(CLAIM), None, 0, "short title is skipped"),
    (COMMENT, [], {guard.OVERRIDE_ENV: "1"}, 0, "bypass env"),
    (COMMENT, None, None, 0, "no transcript_path fails open"),
    ({"command": "gh pr comment 12 --body-file -"}, [], None, 2, "stdin body is unverifiable"),
    ({"command": "gh pr create --fill"}, [], None, 2, "--fill hides the text"),
    ({"command": "gh pr view 12"}, [], None, 0, "reads pass untouched"),
]


def check_e2e(case) -> bool:
    tool_input, entries, env, expect, label = case
    got = run_hook(tool_input, entries, env)
    return _testlib.report(got == expect, f"e2e: {label} (exit {got})")


def check_body_file() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        body = Path(tmp) / "pr.md"
        body.write_text("## Why\n\n" + CLAIM + "\n", encoding="utf-8")
        hit = guard.detect("PowerShell", {"command": f"gh pr create --title WIP --body-file \"{body}\""}, tmp)
        ok = hit is not None and any(CLAIM in v for v in hit.values)
    return _testlib.report(ok, "body file content is what gets checked, Windows path intact")


def check_body_file_msys() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        body = Path(tmp) / "sc.json"
        body.write_text(json.dumps({"text": CLAIM}), encoding="utf-8")
        drive = body.drive.rstrip(":").lower()
        msys_path = "/" + drive + str(body)[len(body.drive):].replace("\\", "/")
        command = f"curl -X POST {SC}/123/comments -d @{msys_path}"
        hit = guard.detect("Bash", {"command": command}, tmp)
        ok = hit is not None and any(CLAIM in v for v in hit.values)
    return _testlib.report(ok, "MSYS /c/... body file path is read on Windows")


def check_mcp_e2e() -> bool:
    tool_input = {"storyPublicId": 1, "text": CLAIM}
    blocked = run_hook(tool_input, [], tool_name="mcp__shortcut__stories-create-comment") == 2
    cleared = run_hook(tool_input, three_inline(CLAIM), tool_name="mcp__shortcut__stories-create-comment") == 0
    return _testlib.report(blocked and cleared, "MCP comment blocks, then clears after 3 PASS")


def main() -> int:
    fails = _testlib.run_cases(DETECT_CASES, check_detect)
    fails += _testlib.run_cases(E2E_CASES, check_e2e)
    if not check_body_file():
        fails.append("body file")
    if not check_body_file_msys():
        fails.append("body file msys")
    if not check_mcp_e2e():
        fails.append("mcp e2e")
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(main())
