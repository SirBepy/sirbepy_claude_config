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

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "shortcut-create-guard.py"
)

URL = "https://api.app.shortcut.com/api/v3/stories"

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
    ("mcp__shortcut__stories-update", None, False, "MCP update tool, guard_mutation's job"),
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
            guard.oldest_fresh_marker(tmpdir, glob, guard.FRESHNESS_SECONDS) is not None, label
        ):
            fails.append(label)

        stale_time = time.time() - (guard.FRESHNESS_SECONDS + 60)
        os.utime(fresh, (stale_time, stale_time))
        label = f"{fresh.name} older than {guard.FRESHNESS_SECONDS}s is ignored"
        if not _testlib.report(
            guard.oldest_fresh_marker(tmpdir, glob, guard.FRESHNESS_SECONDS) is None, label
        ):
            fails.append(label)
        fresh.unlink()

    (tmpdir / ".commit-marker-session-xyz").touch()
    for glob in guard.MARKER_GLOBS:
        label = f"a commit marker never satisfies {glob}"
        if not _testlib.report(
            guard.oldest_fresh_marker(tmpdir, glob, guard.FRESHNESS_SECONDS) is None, label
        ):
            fails.append(label)

sys.exit(_testlib.summarize(fails, style="count"))
