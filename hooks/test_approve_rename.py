"""Self-test for approve-rename.py and for the settings.json wiring of hooks.

Run directly: python hooks/test_approve_rename.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

approve-rename.py auto-allows a PowerShell call only when EVERY statement in it
is an invocation of skills/close/rename-session.ps1. The old PowerShell hook
allowed any command that merely contained the file name, e.g. one ending in
`# rename-session.ps1` or `Remove-Item x; rename-session.ps1`.

The second half pins that every hook script settings.json runs exists, and that
the retired status-marker-guard.py stays out of both.
"""

import json
import re
import sys
from pathlib import Path

import _testlib

HOOKS = Path(__file__).resolve().parent
SETTINGS = HOOKS.parent / "settings.json"
guard = _testlib.load_module("guard", HOOKS / "approve-rename.py")

fails = []

ALLOW_CASES = [
    ('& "C:\\Users\\tecno\\.claude\\skills\\close\\rename-session.ps1" -Close', True, "the /close -Close call"),
    ("~/.claude/skills/close/rename-session.ps1 -GetId", True, "the -GetId call by tilde path"),
    ('$id = & "C:\\Users\\tecno\\.claude\\skills\\close\\rename-session.ps1" -GetId', True, "a -GetId result assigned to a variable"),
    ('powershell -NoProfile -File "C:/Users/tecno/.claude/skills/close/rename-session.ps1" -Name "my chat"', True, "-File form with a quoted -Name"),
    ('& "C:\\Users\\tecno\\.claude\\skills\\close\\rename-session.ps1" -GetId; & "C:\\Users\\tecno\\.claude\\skills\\close\\rename-session.ps1" -Close', True, "two rename calls in one command"),
    ("Write-Output 1 # rename-session.ps1", False, "1278: a trailing comment naming the script is not an invocation"),
    ("echo rename-session.ps1", False, "the file name as an argument of another command"),
    ("Remove-Item -Recurse C:\\x; & C:\\Users\\tecno\\.claude\\skills\\close\\rename-session.ps1 -Close", False, "1278: a destructive statement chained before a rename call"),
    ("& C:\\Users\\tecno\\.claude\\skills\\close\\rename-session.ps1 -Close; Remove-Item -Recurse C:\\x", False, "1278: a destructive statement chained after a rename call"),
    ('& "C:\\somewhere\\else\\rename-session.ps1" -Close', False, "a same-named script outside skills/close"),
    ('& "C:\\Users\\tecno\\.claude\\skills\\close\\rename-session.ps1" -Name "$(Remove-Item x)"', False, "a subexpression inside an argument"),
    ('& "C:\\Users\\tecno\\.claude\\skills\\close\\rename-session.ps1" -Close > out.txt', False, "a redirect"),
    ("", False, "an empty command"),
]


def check_allow(case) -> bool:
    command, expected, label = case
    got = guard.approves(command)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(ALLOW_CASES, check_allow)

# --- settings.json wiring ---

settings_text = SETTINGS.read_text(encoding="utf-8")
settings = json.loads(settings_text)

referenced = set()
for entries in settings.get("hooks", {}).values():
    for entry in entries:
        for hook in entry.get("hooks", []):
            for m in re.finditer(r"hooks[\\/]+([\w.-]+\.py)", hook.get("command", "")):
                referenced.add(m.group(1))

missing = sorted(name for name in referenced if not (HOOKS / name).exists())
if not _testlib.report(not missing, f"every hook script settings.json runs exists (missing: {missing})"):
    fails.append("settings hook scripts exist")

for retired in ("status-marker-guard", "approve-rename.ps1"):
    label = f"settings.json no longer wires {retired}"
    if not _testlib.report(retired not in settings_text, label):
        fails.append(label)

label = "approve-rename.py is wired in settings.json"
if not _testlib.report("approve-rename.py" in referenced, label):
    fails.append(label)

label = "the retired status-marker-guard.py and its test are gone"
if not _testlib.report(
    not (HOOKS / "status-marker-guard.py").exists() and not (HOOKS / "test_status_marker_guard.py").exists(), label
):
    fails.append(label)

sys.exit(_testlib.summarize(fails))
