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
# The canonical token extraction from refs/shortcut-api.md: its `cut -d=` and `tr -d` carry
# -d flags that are not curl data flags.
TOKEN_RECIPE = "TOKEN=$(grep -a '^SHORTCUT_API_TOKEN=' ~/.claude/.env | cut -d= -f2 | tr -d '\\r\"'); "



def py(body: str) -> str:
    """An inline python HTTP script as Bash would see it."""
    return f'python -I -c "import urllib.request as u, json; {body}"'


# (tool_name, tool_input, expect_detected, label)
DETECT_CASES = [
    ("Bash", {"command": f"curl -X POST {SC} -d '{{\"name\": \"{TITLE}\", \"description\": \"{CLAIM}\"}}'"}, True, "Shortcut REST create"),
    ("Bash", {"command": f"curl -X POST {SC}/123/comments -d '{{\"text\": \"{CLAIM}\"}}'"}, True, "Shortcut REST comment"),
    ("Bash", {"command": f"curl -X PUT {SC}/123 -d '{{\"description\": \"{CLAIM}\"}}'"}, True, "Shortcut REST description rewrite"),
    ("Bash", {"command": f"curl -X PUT {SC}/123 -d '{{\"workflow_state_id\": 500000011}}'"}, False, "Shortcut state move stays ungated"),
    ("Bash", {"command": f"curl -G {SC}/search -d query=biller"}, False, "Shortcut search read"),
    ("Bash", {"command": f"for id in 1 2; do curl -s \"{SC}/$id\" -H \"Shortcut-Token: $TOKEN\" -o /c/tmp/s_$id.json; done"}, False, "GET loop with a $id URL passes"),
    ("Bash", {"command": f"for id in 1 2; do curl -s \"{SC}/${{id}}\" -o /c/tmp/s.json; done"}, False, "GET loop with a ${id} URL passes"),
    ("Bash", {"command": TOKEN_RECIPE + f"for s in 54369 54384; do curl -s -H \"Shortcut-Token: $TOKEN\" {SC}/$s | python -c \"import sys,json; print(json.load(sys.stdin)['id'])\"; done"}, False, "cut -d= token recipe plus a GET loop passes"),
    ("Bash", {"command": TOKEN_RECIPE + f"curl -s -H \"Shortcut-Token: $TOKEN\" {SC}/54369"}, False, "cut -d= token recipe plus a literal GET passes"),
    ("Bash", {"command": TOKEN_RECIPE + f"curl -s -H \"Shortcut-Token: $TOKEN\" \"{SC}?archived=false\""}, False, "cut -d= recipe is not a data flag on a bare /stories read"),
    ("PowerShell", {"command": f"foreach ($id in 1, 2) {{ Invoke-RestMethod -Uri \"{SC}/$id\" -Headers $h }}"}, False, "PowerShell GET loop with a $id URL passes"),
    ("Bash", {"command": f"for id in 1 2; do curl -X POST {SC}/$id/comments -d '{{\"text\": \"{CLAIM}\"}}'; done"}, True, "comment POST in a loop with literal text stays gated"),
    ("Bash", {"command": f"for id in 1 2; do curl -X POST {SC}/$id/comments -d \"$BODY\"; done"}, True, "comment POST to $id with a variable body stays gated"),
    ("Bash", {"command": f"curl -X POST {SC}/${{id}}/comments -d \"$BODY\""}, True, "comment POST to ${id} with a variable body stays gated"),
    ("PowerShell", {"command": f"Invoke-RestMethod -Uri \"{SC}/$($s.id)/comments\" -Method Post -Body $b"}, True, "PowerShell comment POST to $($s.id) stays gated"),
    ("PowerShell", {"command": f"Invoke-RestMethod -Uri \"{SC}/$($a + 1)/comments\" -Method Post -Body $b"}, True, "PowerShell comment POST to a spaced $(...) id stays gated"),
    ("Bash", {"command": TOKEN_RECIPE + f"curl -X POST {SC} -d \"$BODY\""}, True, "create via -X POST after the cut -d= recipe stays gated"),
    ("Bash", {"command": TOKEN_RECIPE + f"curl -s {SC} -d '{{\"name\": \"{TITLE}\", \"description\": \"{CLAIM}\"}}'"}, True, "create via -d with no -X after the recipe stays gated"),
    ("Bash", {"command": TOKEN_RECIPE + f"for id in 1 2; do curl -sd '{{\"description\": \"{CLAIM}\"}}' {SC}/$id; done"}, True, "clustered -sd description rewrite in a loop stays gated"),
    ("Bash", {"command": f"for id in 1 2; do curl --data-raw '{{\"description\": \"{CLAIM}\"}}' {SC}/$id; done"}, True, "--data-raw description rewrite in a loop stays gated"),
    ("Bash", {"command": f"bash -c \"curl -d '{{\\\"name\\\": \\\"{TITLE}\\\"}}' {SC}\""}, True, "curl write hidden in a bash -c string stays gated"),
    ("Bash", {"command": f"xargs curl -d \"$BODY\" {SC}"}, True, "curl behind xargs with a data flag stays gated"),
    # An unquoted newline separates statements: a leading NON_HTTP command on line 1 must not
    # hide the data flag of the curl on line 2.
    ("Bash", {"command": f"ls\ncurl -d \"$BODY\" {SC}/12/comments"}, True, "ls newline curl -d comment stays gated"),
    ("Bash", {"command": f"date\ncurl -s -d \"$BODY\" {SC}/12/comments"}, True, "date newline curl -s -d comment stays gated"),
    ("Bash", {"command": f"cut -d= -f2 .env\ncurl -d \"$BODY\" {SC}/12/comments"}, True, "cut -d= newline curl -d comment stays gated"),
    ("Bash", {"command": f"ls\r\ncurl -d \"$BODY\" {SC}/12/comments"}, True, "CRLF line break separates statements too"),
    ("Bash", {"command": f"curl -s \\\n  -d \"$BODY\" {SC}/12/comments"}, True, "backslash-newline continuation keeps the data flag on the curl"),
    ("PowerShell", {"command": f"Get-Date\nInvoke-RestMethod -Uri {SC}/12/comments -Method Post -Body $b"}, True, "PowerShell newline then a comment POST stays gated"),
    ("Bash", {"command": TOKEN_RECIPE.replace("; ", "\n") + f"for id in 1 2\ndo\n  curl -s -H \"Shortcut-Token: $TOKEN\" \"{SC}/$id\"\ndone"}, False, "multi-line cut -d= recipe plus a GET loop passes"),
    ("Bash", {"command": f"curl -s {SC}/5 -H \"X-Note: a\nb\" -d x -G"}, False, "a quoted newline does not split and -G keeps it a read"),
    # Fail closed on an expansion the id pattern cannot classify.
    ("Bash", {"command": f"curl -X POST \"{SC}/$(echo $(date))/comments\" -d \"$B\""}, True, "nested $(...) id with a variable comment body stays gated"),
    ("Bash", {"command": f"curl -X POST {SC}/$id/$kind -d \"$B\""}, True, "variable segment after the id with a variable body is gated"),
    ("Bash", {"command": f"curl -X POST {SC}/123/$kind -d \"$B\""}, True, "variable segment after a literal id is gated"),
    ("Bash", {"command": f"curl -X POST \"{SC}/`date`/comments\" -d \"$B\""}, True, "backtick id with a variable comment body stays gated"),
    ("Bash", {"command": f"curl -X POST \"{SC}/$(echo $(date)\" -d \"$B\""}, True, "unbalanced $( in the id path is gated"),
    ("Bash", {"command": f"curl -s \"{SC}/$(echo $(date))\" -H \"Shortcut-Token: $TOKEN\" -d x -G"}, False, "nested $(...) id on a GET passes"),
    ("Bash", {"command": f"curl -X PUT {SC}/$id/history -d '{{\"workflow_state_id\": 5}}'"}, False, "literal non-comment path after a $id stays ungated"),
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
    # Quoted text that merely NAMES a request sends nothing; only a program in command position does.
    ("Bash", {"command": f"echo \"curl -X POST {SC} -d '{{\\\"name\\\": \\\"{TITLE}\\\"}}'\""}, False, "echo of a curl create is prose"),
    ("Bash", {"command": f"git commit -m \"DOCS: note that curl -X POST {SC} -d x creates a story\" -- f.md"}, False, "commit message quoting a curl create"),
    ("Bash", {"command": f"grep -n \"curl -X PUT {SC}/123 -d\" notes.md"}, False, "grep pattern naming a curl rewrite"),
    ("PowerShell", {"command": f"Write-Host \"Invoke-RestMethod -Method Post -Uri {SC} -Body x\""}, False, "Write-Host of an IRM create is prose"),
    ("Bash", {"command": f"echo ok; curl -X POST {SC} -d \"$BODY\""}, True, "a real create after an echo statement stays gated"),
    ("PowerShell", {"command": f"$r = Invoke-RestMethod -Method Post -Uri {SC} -Body $b"}, True, "an assigned IRM create stays gated"),
    ("Bash", {"command": f"echo go\ncurl -H \"A: b\" {SC} \\\n  -d '{{\"name\": \"{TITLE}\", \"description\": \"{CLAIM}\"}}'"}, True, "a continued curl -d create next to an echo stays gated"),
    ("Bash", {"command": f"curl {SC} \\\n  -d \"$BODY\"\necho done"}, True, "a continued curl -d create before an echo stays gated"),
    ("PowerShell", {"command": f"& \"C:\\Windows\\System32\\curl.exe\" -X POST {SC} -d \"$BODY\""}, True, "a create through a quoted exe path stays gated"),
    ("Bash", {"command": f"timeout 30 curl -X POST {SC} -d \"$BODY\""}, True, "a create behind timeout stays gated"),
    ("Bash", {"command": f"echo \"curl -X POST {SC} -d x\" | bash"}, True, "display text piped into bash is executed"),
    ("Bash", {"command": f"bash <<'EOF'\ncurl -X POST {SC} -d \"$BODY\"\nEOF"}, True, "a create inside a heredoc fed to bash stays gated"),
    ("PowerShell", {"command": f"Start-Process -FilePath curl.exe -ArgumentList \"-X POST {SC} -d x\""}, True, "Start-Process -FilePath curl.exe stays gated"),
    ("Bash", {"command": f"echo \"$(curl -X POST {SC} -d \\\"$BODY\\\")\""}, True, "a curl inside a command substitution in a string stays gated"),
    ("Bash", {"command": f"echo 'it'\"'\"'s'; curl -X POST {SC} -d \"$BODY\""}, True, "odd quoting that desyncs the mask keeps the create gated"),
    # pc-1329: an inline python script names its verb in the call, not in a curl-style flag.
    ("Bash", {"command": py(f"u.urlopen(u.Request('{SC}', data=json.dumps({{'name': '{TITLE}', 'description': '{CLAIM}'}}).encode(), method='POST'))")}, True, "python urllib story create"),
    ("Bash", {"command": py(f"u.urlopen(u.Request('{SC}/123/comments', data=json.dumps({{'text': '{CLAIM}'}}).encode(), method='POST'))")}, True, "python urllib comment POST"),
    ("Bash", {"command": py(f"u.urlopen(u.Request('{SC}/123/comments/456', data=json.dumps({{'text': '{CLAIM}'}}).encode(), method='PUT'))")}, True, "python urllib comment edit"),
    ("Bash", {"command": py(f"u.urlopen(u.Request('{SC}/123', data=json.dumps({{'description': '{CLAIM}'}}).encode(), method='PUT'))")}, True, "python urllib description rewrite"),
    ("Bash", {"command": py(f"u.urlopen(u.Request('{SC}/123', data=json.dumps({{'description': '{CLAIM}'}}).encode()))")}, True, "python urllib data with no method is a POST"),
    ("Bash", {"command": py(f"import requests; requests.post('{SC}/123/comments', json={{'text': '{CLAIM}'}})")}, True, "python requests.post comment"),
    ("Bash", {"command": py(f"import kickoff; t = kickoff.env()['SHORTCUT_API_TOKEN']; u.urlopen(u.Request(API + '/stories/123/comments', data=json.dumps({{'text': '{CLAIM}'}}).encode(), method='POST'))")}, True, "python comment POST with the URL assembled from a base"),
    ("Bash", {"command": py("import kickoff; t = kickoff.env(); u.urlopen(u.Request(API + '/stories', data=body, method='POST'))")}, True, "python create with an opaque body is gated"),
    ("Bash", {"command": f"python -c \"import urllib.request as u, json; u.urlopen(u.Request('{SC}/123/comments', data=json.dumps({{\\\"text\\\": \\\"{CLAIM}\\\"}}).encode(), method='POST'))\""}, True, "python comment POST with backslash-escaped quotes"),
    ("PowerShell", {"command": f"python -c \"import urllib.request as u; u.urlopen(u.Request('{SC}/123/comments', data=json.dumps({{'text': '{CLAIM}'}}).encode(), method='POST'))\""}, True, "python comment POST from the PowerShell tool"),
    ("Bash", {"command": py(f"u.urlopen(u.Request('{SC}/123/comments', json.dumps({{'text': '{CLAIM}'}}).encode()))")}, True, "python Request with the body as a positional argument"),
    ("Bash", {"command": py(f"import requests, kickoff; s = requests.Session(); s.headers['Shortcut-Token'] = kickoff.env()['SHORTCUT_API_TOKEN']; s.post(API + '/stories/123/comments', json={{'text': '{CLAIM}'}})")}, True, "python Session.post comment"),
    ("Bash", {"command": py(f"import kickoff; kickoff.env(); client.put(f\"{{API}}/stories/123\", json={{'description': '{CLAIM}'}})")}, True, "python client.put description rewrite"),
    ("Bash", {"command": py("r = u.Request('https://api.github.com/repos/o/r/pulls'); data = json.load(u.urlopen(r))")}, False, "python GitHub GET storing into a variable named data"),
    ("Bash", {"command": py("r = u.Request('https://api.app.shortcut.com/api/v3/epics/5/stories', headers={'Shortcut-Token': 'x'}); data = json.load(u.urlopen(r))")}, False, "python GET of an epic's stories storing into data"),
    ("Bash", {"command": py(f"print(u.urlopen('{SC}/123').read())")}, False, "python GET passes"),
    ("Bash", {"command": py(f"print(u.urlopen(u.Request('{SC}/123/comments', method='GET')).read())")}, False, "python explicit GET of comments passes"),
    ("Bash", {"command": py("import kickoff; t = kickoff.env()['SHORTCUT_API_TOKEN']; print(u.urlopen(u.Request(API + '/stories/123', headers={'Shortcut-Token': t})).read())")}, False, "python GET with the token plumbing passes"),
    ("Bash", {"command": py(f"u.urlopen(u.Request('{SC}/123', data=json.dumps({{'workflow_state_id': 500000011}}).encode(), method='PUT'))")}, False, "python state move stays ungated"),
    ("Bash", {"command": py("u.urlopen(u.Request(API + '/stories/123', data=b'{}', method='PUT'))")}, False, "python id-only PUT from a base URL stays ungated"),
    ("Bash", {"command": f"echo \"python -c u.Request('{SC}/123/comments', method='POST')\""}, False, "echo of a python comment POST is prose"),
    # pc-review item 10: per-call method inference, and /stories/bulk is a create.
    ("Bash", {"command": py(f"u.urlopen(u.Request('{SC}/123', method='GET')); u.urlopen(u.Request('{SC}', data=body))")}, True, "python GET call then a body-carrying create call is gated"),
    ("Bash", {"command": f"curl -X POST {SC}/bulk -d '{{\"stories\": [{{\"workflow_state_id\": 5}}]}}'"}, True, "curl POST to /stories/bulk with no visible prose is gated"),
    ("Bash", {"command": f"curl -s {SC}/123 -o /c/tmp/s.json; curl -X POST {SC} -d '{{\"project_id\": 5}}'"}, True, "a read of one story ahead of a bare create does not hide it"),
    ("Bash", {"command": py("import kickoff; kickoff.env(); u.urlopen(u.Request(API + '/stories/bulk', data=body, method='POST'))")}, True, "python POST to /stories/bulk from a base URL is gated"),
    ("Bash", {"command": py("import kickoff; kickoff.env(); u.urlopen(u.Request(API + '/stories/bulk', data=b'{\"story_ids\": [1]}', method='PUT'))")}, False, "python bulk PUT with no prose stays ungated"),
    ("Bash", {"command": f"curl -X PUT {SC}/bulk -H 'Content-Type: application/json' -d '{{\"story_ids\": [1, 2], \"workflow_state_id\": 500}}'"}, False, "a bulk state move stays ungated"),
    ("Bash", {"command": f"curl -X DELETE {SC}/bulk -d '{{\"story_ids\": [1, 2]}}'"}, False, "a bulk delete stays ungated"),
    ("Bash", {"command": f"curl -X PUT {SC}/12 -d '{{\"workflow_state_id\": 500}}' && curl -s {SC}/12/comments"}, False, "a state move followed by a comment read stays ungated"),
    ("Bash", {"command": f"curl -X PUT {SC}/bulk -d '{{\"story_ids\": [1]}}'; curl -X POST {SC} -d '{{\"project_id\": 5}}'"}, True, "a bare create after a bulk PUT is gated"),
    ("Bash", {"command": f"curl -X PUT {SC}/12 -d '{{\"workflow_state_id\": 5}}'; curl -X POST {SC}/12/comments -d \"$BODY\""}, True, "a comment POST after a state move is gated"),
    ("Bash", {"command": f"curl -s {SC}/12 -o /c/tmp/s.json; curl -X POST {SC}/12/comments -d \"$BODY\""}, True, "a comment POST after a read is gated"),
    ("Bash", {"command": f"curl -X PUT -H 'Content-Type: application/json; charset=utf-8' -H 'Shortcut-Token: x' {SC}/bulk -d '{{\"story_ids\": [1], \"workflow_state_id\": 5}}'"}, False, "a semicolon inside a header does not hide the bulk PUT verb"),
    ("Bash", {"command": f"curl -X PUT {SC}/bulk -d '{{\"story_ids\": [1]}}' & curl -X POST {SC}/bulk -d '{{\"story_ids\": [2]}}'"}, True, "a bulk POST after a backgrounded bulk PUT is gated"),
    ("Bash", {"command": f"curl -X PUT \\\r\n {SC}/bulk -d '{{\"story_ids\": [1]}}'"}, False, "a CRLF line continuation keeps the verb on the bulk statement"),
]


def check_detect(case) -> bool:
    tool_name, tool_input, expect, label = case
    got = guard.detect(tool_name, tool_input, None) is not None
    return _testlib.report(got == expect, f"detect: {label} (got {got})")


# (url tail after /stories, expected `rest` capture): a shell variable in the id slot is part of
# the path, so it must not truncate `rest` to "" (the shape of a bare create).
REST_CASES = [
    ("/$id", "/$id"),
    ("/${id}", "/${id}"),
    ("/$id/comments", "/$id/comments"),
    ("/$($s.id)/comments", "/$($s.id)/comments"),
    ("/123/comments", "/123/comments"),
    ("", ""),
    ("?archived=false", ""),
]


# (url tail after /stories, whether the write must carry visible prose). /bulk creates many
# stories at once, so it is gated like a bare create; an id-only update is not.
REQUIRES_CASES = [
    ("/bulk", True),
    ("/bulk/", True),
    ("/123", False),
    ("/123/comments", True),
    ("", True),
]


def check_requires(case) -> bool:
    tail, expect = case
    command = "curl -X POST https://api.app.shortcut.com/api/v3/stories" + tail
    got = guard.shortcut_requires_prose(command, guard.SHORTCUT_URL_RE.search(command))
    return _testlib.report(got == expect, f"requires prose: stories{tail} (got {got})")


def check_rest(case) -> bool:
    tail, expect = case
    m = guard.SHORTCUT_URL_RE.search("https://api.app.shortcut.com/api/v3/stories" + tail)
    got = m.group("rest") if m else None
    return _testlib.report(got == expect, f"rest capture: stories{tail} (got {got!r})")


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
PY_COMMENT = {"command": py(f"u.urlopen(u.Request('{SC}/12/comments', data=json.dumps({{'text': '{CLAIM}'}}).encode(), method='POST'))")}
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
    ({"command": f"ls\ncurl -d @body.json {SC}/12/comments"}, [], None, 2, "ls newline curl -d @file comment is denied (unreadable body)"),
    ({"command": f"curl -X POST \"{SC}/$(echo $(date))/comments\" -d \"$B\""}, [], None, 2, "nested substitution id comment POST is denied"),
    ({"command": f"curl -s \"{SC}/$(echo $(date))\" -G"}, [], None, 0, "nested substitution id GET is allowed"),
    (PY_COMMENT, [], None, 2, "python comment POST without verifiers is denied (pc-1329)"),
    (PY_COMMENT, three_inline(CLAIM), None, 0, "python comment POST clears after 3 PASS"),
    (PY_COMMENT, three_inline(OTHER), None, 2, "python comment POST of unverified text is denied"),
    ({"command": py(f"print(u.urlopen('{SC}/12').read())")}, [], None, 0, "python GET passes untouched"),
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


def check_infile_trailing_punct() -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        body = Path(tmp) / "sc.json"
        body.write_text(json.dumps({"text": CLAIM}), encoding="utf-8")
        ok = True
        for tail in (";", ",", ")"):
            command = (f"Invoke-RestMethod -Method Post -Uri {SC}/123/comments "
                       f"-InFile {body}{tail} \"done\"")
            try:
                hit = guard.detect("PowerShell", {"command": command}, tmp)
            except guard.Unverifiable:
                hit = None
            ok = ok and hit is not None and any(CLAIM in v for v in hit.values)
        # A path the guard cannot read stays Unverifiable, punctuation or not.
        missing = Path(tmp) / "missing.json"
        try:
            guard.detect("PowerShell", {"command": (f"Invoke-RestMethod -Method Post -Uri {SC}/123/comments "
                                                    f"-InFile {missing}; \"done\"")}, tmp)
            denied = False
        except guard.Unverifiable:
            denied = True
    return _testlib.report(ok and denied, "-InFile path drops trailing ; , ) and a missing file is still Unverifiable")


def check_mcp_e2e() -> bool:
    tool_input = {"storyPublicId": 1, "text": CLAIM}
    blocked = run_hook(tool_input, [], tool_name="mcp__shortcut__stories-create-comment") == 2
    cleared = run_hook(tool_input, three_inline(CLAIM), tool_name="mcp__shortcut__stories-create-comment") == 0
    return _testlib.report(blocked and cleared, "MCP comment blocks, then clears after 3 PASS")


def main() -> int:
    fails = _testlib.run_cases(DETECT_CASES, check_detect)
    fails += _testlib.run_cases(REST_CASES, check_rest)
    fails += _testlib.run_cases(REQUIRES_CASES, check_requires)
    fails += _testlib.run_cases(E2E_CASES, check_e2e)
    if not check_body_file():
        fails.append("body file")
    if not check_body_file_msys():
        fails.append("body file msys")
    if not check_infile_trailing_punct():
        fails.append("infile trailing punctuation")
    if not check_mcp_e2e():
        fails.append("mcp e2e")
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(main())
