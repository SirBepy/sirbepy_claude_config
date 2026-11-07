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

HOME_WIN = str(Path.home())
HOME_FWD = Path.home().as_posix()
R_WIN = HOME_WIN + "\\.claude\\skills\\close\\rename-session.ps1"
R_FWD = HOME_FWD + "/.claude/skills/close/rename-session.ps1"

ALLOW_CASES = [
    (f'& "{R_WIN}" -Close', True, "the /close -Close call"),
    ("~/.claude/skills/close/rename-session.ps1 -GetId", True, "the -GetId call by tilde path"),
    (f'$id = & "{R_WIN}" -GetId', True, "a -GetId result assigned to a variable"),
    (f'powershell -NoProfile -File "{R_FWD}" -Name "my chat"', True, "-File form with a quoted -Name"),
    (f'& "{R_WIN}" -GetId; & "{R_WIN}" -Close', True, "two rename calls in one command"),
    ("Write-Output 1 # rename-session.ps1", False, "a trailing comment naming the script is not an invocation"),
    ("echo rename-session.ps1", False, "the file name as an argument of another command"),
    (f"Remove-Item -Recurse C:\\x; & {R_WIN} -Close", False, "a destructive statement chained before a rename call"),
    (f"& {R_WIN} -Close; Remove-Item -Recurse C:\\x", False, "a destructive statement chained after a rename call"),
    ('& "C:\\somewhere\\else\\rename-session.ps1" -Close', False, "a same-named script outside skills/close"),
    (f'& "{R_WIN}" -Name "$(Remove-Item x)"', False, "a subexpression inside an argument"),
    (f'& "{R_WIN}" -Close > out.txt', False, "a redirect"),
    ("", False, "an empty command"),
    # Review findings: an unanchored tail, argument expressions, and -Command.
    ("C:/evil/skills/close/rename-session.ps1 -Close", False, "an attacker-chosen directory ending in skills/close"),
    ("cmd/skills/close/rename-session.ps1 -Close", False, "a relative path ending in the right tail"),
    (f"powershell -File C:/evil/skills/close/rename-session.ps1", False, "-File pointing outside the home skills dir"),
    (f"& {R_WIN} -Title x -Foo (Remove-Item C:/x)", False, "a parenthesised expression evaluated as an argument"),
    (f"& {R_WIN} -Foo @(Remove-Item C:/x)", False, "an array expression as an argument"),
    (f"& {R_WIN} -Foo {{Remove-Item C:/x}}", False, "a script block as an argument"),
    (f"powershell -Command Remove-Item C:/x -File {R_FWD}", False, "-Command swallows the rest, -File is just text"),
    (f"& {R_WIN} -Name x\nRemove-Item C:/x", False, "a second statement on the next line"),
    (f"& {R_WIN} -Close\rRemove-Item C:/x", False, "a bare carriage return separates PowerShell statements"),
    (f'powershell -com "Remove-Item C:/x" -File {R_FWD}', False, "-com is an unambiguous prefix of -Command"),
    (f"powershell -enc abc -File {R_FWD}", False, "-enc is a prefix of -EncodedCommand"),
    (f'pwsh -comm "Remove-Item C:/x" -File {R_FWD}', False, "pwsh -comm"),
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
