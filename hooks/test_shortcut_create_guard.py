"""Self-test for shortcut-create-guard.py.

Run directly: python hooks/test_shortcut_create_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import importlib.util
import sys
import tempfile
import time
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "guard", Path(__file__).resolve().parent / "shortcut-create-guard.py"
)
guard = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(guard)

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

failures = 0
for tool_name, command, expected, label in CASES:
    tool_input = {"command": command} if command is not None else {}
    got = guard.is_story_creation(tool_name, tool_input)
    ok = got == expected
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected creation={expected}, got {got})")

# Marker freshness: the guard allows only on a marker inside the window.
with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    fresh = tmpdir / ".shortcut-marker-abc"
    fresh.touch()
    found = guard.oldest_fresh_marker(tmpdir, guard.MARKER_GLOB, guard.FRESHNESS_SECONDS)
    ok = found is not None
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}: fresh marker is found")

    stale_time = time.time() - (guard.FRESHNESS_SECONDS + 60)
    import os
    os.utime(fresh, (stale_time, stale_time))
    found = guard.oldest_fresh_marker(tmpdir, guard.MARKER_GLOB, guard.FRESHNESS_SECONDS)
    ok = found is None
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}: marker older than {guard.FRESHNESS_SECONDS}s is ignored")

    fresh.unlink()
    (tmpdir / ".commit-marker-session-xyz").touch()
    found = guard.oldest_fresh_marker(tmpdir, guard.MARKER_GLOB, guard.FRESHNESS_SECONDS)
    ok = found is None
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}: a commit marker never satisfies this guard")

print(f"\n{'ALL PASS' if not failures else str(failures) + ' FAILURE(S)'}")
sys.exit(1 if failures else 0)
