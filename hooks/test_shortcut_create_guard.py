"""Self-test for shortcut-create-guard.py.

Run directly: python hooks/test_shortcut_create_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import os
import sys
import tempfile
import time
from pathlib import Path

import _testlib
from _hooklib import oldest_fresh_marker

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "shortcut-create-guard.py"
)

URL = "https://api.app.shortcut.com/api/v3/stories"


def py(body: str) -> str:
    """An inline python HTTP script as Bash would see it."""
    return f'python -I -c "import urllib.request as u; {body}"'


# (tool_name, command, expect_creation, label)
CASES = [
    ("Bash", f'curl -s -X POST "{URL}" -H "Shortcut-Token: $TOKEN" -d @payload.json', True, "curl -X POST to /stories"),
    ("Bash", f'curl -XPOST "{URL}" -d @payload.json', True, "curl -XPOST, no space"),
    ("Bash", f'curl --request POST "{URL}" -d @payload.json', True, "curl --request POST"),
    ("Bash", f'curl -s "{URL}" -d @payload.json', True, "bare -d defaults to POST"),
    ("PowerShell", f'Invoke-RestMethod -Method Post -Uri "{URL}" -Body $json', True, "IRM -Method Post"),
    ("mcp__shortcut__stories-create", None, True, "MCP create tool"),
    # Everything below must pass through untouched.
    ("Bash", 'curl -s -G "https://api.app.shortcut.com/api/v3/search/stories" --data-urlencode "query=biller"', False, "the ground check's own search query"),
    ("Bash", f'curl -X PUT "{URL}/12345" -d @patch.json', False, "PUT to /stories/<id> is an update"),
    ("Bash", f'curl -X POST "{URL}/12345/comments" -d @c.json', False, "POST to /stories/<id>/comments"),
    ("Bash", f'curl -s "{URL}/12345" -H "Shortcut-Token: $TOKEN"', False, "plain GET of one story"),
    ("Bash", f'echo "we POST to {URL} in the skill"', False, "URL mentioned in prose, no data flag"),
    ("Bash", f'echo "curl -X POST {URL} -d x"', False, "echo of a curl create is prose, not a create"),
    ("Bash", f"echo 'curl -X POST {URL} -d x'", False, "single-quoted echo of a curl create"),
    ("Bash", f'git commit -m "DOCS: curl -X POST {URL} -d @p.json files a story" -- f.md', False, "commit message quoting a curl create"),
    ("PowerShell", f'Write-Output "Invoke-RestMethod -Method Post -Uri {URL}"', False, "Write-Output of an IRM create"),
    ("Bash", f'echo go; curl -X POST "{URL}" -d @p.json', True, "a real create after another statement"),
    ("Bash", f'bash -c "curl -X POST {URL} -d @p.json"', True, "a create inside bash -c"),
    ("Bash", f'TOKEN=abc curl -X POST "{URL}" -d @p.json', True, "a create behind an env assignment"),
    ("Bash", f'xargs curl -X POST "{URL}" -d @p.json', True, "a create behind xargs"),
    ("PowerShell", f'$r = Invoke-RestMethod -Method Post -Uri "{URL}" -Body $json', True, "an assigned IRM create"),
    ("PowerShell", f'& curl.exe -X POST "{URL}" -d @p.json', True, "a create behind the call operator"),
    # Shapes an allow-list of command positions missed: anything not plainly display text stays gated.
    ("PowerShell", f'& "C:\\Windows\\System32\\curl.exe" -X POST "{URL}" -d @p.json', True, "a create through a quoted exe path"),
    ("Bash", f'timeout 30 curl -X POST "{URL}" -d @p.json', True, "a create behind timeout"),
    ("Bash", f'cmd /c curl -X POST "{URL}" -d @p.json', True, "a create behind cmd /c"),
    ("Bash", f'./post.sh -X POST "{URL}" -d @p.json', True, "a create through a wrapper script"),
    ("Bash", f'eval "curl -X POST {URL} -d x"', True, "a create inside eval"),
    ("Bash", f'echo "curl -X POST {URL} -d x" | bash', True, "display text piped into bash is executed"),
    ("Bash", f"bash <<'EOF'\ncurl -X POST {URL} -d x\nEOF", True, "a create inside a heredoc fed to bash"),
    ("Bash", f'echo "$(curl -X POST {URL} -d x)"', True, "a command substitution inside echo runs"),
    ("Bash", f'cd "x y" && curl -X POST "{URL}" -d x', True, "a create after a quoted cd"),
    ("Bash", f'echo hi & curl -X POST "{URL}" -d x', True, "a create after a background ampersand"),
    ("PowerShell", f'Write-Host (Invoke-RestMethod -Method Post -Uri {URL} -Body $b )', True, "a PowerShell subexpression inside Write-Host runs"),
    ("Bash", f'echo "curl -X POST {URL} -d x" | sudo bash', True, "display text piped into sudo bash"),
    ("Bash", f'echo "curl -X POST {URL} -d x" | timeout 5 bash', True, "display text piped into timeout bash"),
    ("PowerShell", f'Write-Output "irm -Method Post {URL}" | % {{ iex $_ }}', True, "display text piped into a ForEach-Object iex"),
    ("Bash", f'echo "curl -X POST {URL} -d x" > s.sh && ./s.sh', True, "display text written to a script and run"),
    ("Bash", f'echo "curl -X POST {URL} -d x" \\\n| bash', True, "a pipe on the next line after a continuation backslash"),
    ("PowerShell", f'Write-Output "Invoke-RestMethod -Method Post -Uri {URL}"\r\n  | iex', True, "a pipe on the next line, CRLF and indented"),
    ("Bash", f'echo "curl -X POST {URL} -d x" >&1.sh; bash 1.sh', True, ">&1.sh is a file target, not an fd"),
    ("Bash", f'echo "curl -X POST {URL} -d x" >/dev/null.sh; bash null.sh', True, ">/dev/null.sh is a file target"),
    ("Bash", f"rg --pre 'curl -X POST {URL} -d x' foo .", True, "rg --pre runs its argument"),
    ("Bash", f"git grep -O'curl -X POST {URL} -d x' foo", True, "git grep -O runs its argument"),
    ("Bash", f"curl -s {URL} \\\necho -d x", True, "a continuation line starting with echo is a curl argument"),
    ("Bash", f'echo "curl -X POST {URL} -d x" 2>&1', False, "an fd redirect does not make an echo run anything"),
    ("Bash", f'echo "curl -X POST {URL} -d x" > /dev/null', False, "echo to the null device runs nothing"),
    # A python one-liner carries its verb in the call, not in a curl-style flag.
    ("Bash", py(f"u.urlopen(u.Request('{URL}', data=b'{{}}', method='POST'))"), True, "python urllib Request method='POST' to /stories"),
    ("Bash", py(f"u.urlopen(u.Request('{URL}', data=b'{{}}'))"), True, "python urllib Request with data and no method is a POST"),
    ("Bash", py(f"import requests; requests.post('{URL}', json={{'name': 'x'}})"), True, "python requests.post to /stories"),
    ("Bash", py("import kickoff; t = kickoff.env()['SHORTCUT_API_TOKEN']; u.urlopen(u.Request(API + '/stories', data=b'{}', method='POST'))"), True, "python create with the URL assembled from a base"),
    ("Bash", f"python - <<'EOF'\nimport urllib.request as u\nu.urlopen(u.Request('{URL}', data=b'{{}}', method='POST'))\nEOF", True, "python heredoc create"),
    ("PowerShell", f"python -c \"import urllib.request as u; u.urlopen(u.Request('{URL}', data=b'{{}}', method='POST'))\"", True, "python create from the PowerShell tool"),
    ("Bash", py(f"print(u.urlopen('{URL}/12345').read())"), False, "python GET of one story stays unblocked"),
    ("Bash", py(f"print(u.urlopen(u.Request('{URL}/search', method='GET')).read())"), False, "python explicit GET stays unblocked"),
    ("Bash", py(f"u.urlopen(u.Request('{URL}/12345', data=b'{{}}', method='PUT'))"), False, "python PUT to /stories/<id> is an update"),
    ("Bash", py(f"u.urlopen(u.Request('{URL}/12345/comments', data=b'{{}}', method='POST'))"), False, "python comment POST is not a create"),
    ("Bash", py("import kickoff; u.urlopen(u.Request(API + '/search/stories', data=b'{}', method='POST'))"), False, "python POST to search/stories is not a create"),
    ("Bash", f"echo \"python -c u.Request('{URL}', method='POST')\"", False, "echo of a python create is prose"),
    ("mcp__shortcut__stories-update", None, False, "MCP update tool, shortcut-mutation-guard's job"),
    ("Bash", "git commit -m 'FEAT: stories'", False, "unrelated command"),
    ("Read", None, False, "non-shell tool"),
]


def check(case) -> bool:
    tool_name, command, expected, label = case
    tool_input = {"command": command} if command is not None else {}
    got = guard.is_story_creation(tool_name, tool_input)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected creation={expected}, got {got})")
    return ok


fails = _testlib.run_cases(CASES, check)

# Marker freshness, per accepted name. `.outbound-marker*` is the shared one written by
# refs/outbound-ground-check.md; `.shortcut-marker*` is the legacy name kept working.
MARKER_NAMES = {".outbound-marker*": ".outbound-marker-abc", ".shortcut-marker*": ".shortcut-marker-abc"}

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    for glob in guard.MARKER_GLOBS:
        fresh = tmpdir / MARKER_NAMES[glob]
        fresh.touch()
        label = f"fresh {fresh.name} is found"
        if not _testlib.report(
            oldest_fresh_marker(tmpdir, glob, guard.FRESHNESS_SECONDS) is not None, label
        ):
            fails.append(label)

        stale_time = time.time() - (guard.FRESHNESS_SECONDS + 60)
        os.utime(fresh, (stale_time, stale_time))
        label = f"{fresh.name} older than {guard.FRESHNESS_SECONDS}s is ignored"
        if not _testlib.report(
            oldest_fresh_marker(tmpdir, glob, guard.FRESHNESS_SECONDS) is None, label
        ):
            fails.append(label)
        fresh.unlink()

    (tmpdir / ".commit-marker-session-xyz").touch()
    for glob in guard.MARKER_GLOBS:
        label = f"a commit marker never satisfies {glob}"
        if not _testlib.report(
            oldest_fresh_marker(tmpdir, glob, guard.FRESHNESS_SECONDS) is None, label
        ):
            fails.append(label)

sys.exit(_testlib.summarize(fails, style="count"))
