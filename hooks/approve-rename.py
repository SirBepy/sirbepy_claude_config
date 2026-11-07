"""PreToolUse hook (PowerShell): auto-approve /close's rename helper.

Allows a PowerShell call only when EVERY statement in it invokes
`skills/close/rename-session.ps1` (directly, via the `&` call operator, as
the right side of a `$var = ...` assignment, or through `powershell -File`).
The hook it replaces (skills/close/approve-rename.ps1) allowed any command
whose text merely contained the file name, so `Remove-Item x; rename-session.ps1`
and a trailing `# rename-session.ps1` comment both rode the approval, and it
cold-started a PowerShell process on every PowerShell call.

Stays out of the way (no decision, normal permission flow) on anything it
does not recognise, and on any error. A subexpression, backtick or redirect
anywhere in the command disqualifies it: those can run or write something the
statement split cannot see.
"""

import json
import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    import _hookboot  # retries a shared module another session is mid-way through writing
    from _hooklib import read_payload, basename, split_command_segments, tokenize_command
except Exception as e:
    sys.stderr.write(f"[approve-rename] cannot import _hooklib ({e}); making no decision.\n")
    sys.exit(0)

SCRIPT_TAIL = "/skills/close/rename-session.ps1"
POWERSHELL_EXES = {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}
BARE_ASSIGNMENT_RE = re.compile(r"^\$\w+\s*=\s*$")
ASSIGNMENT_PREFIX_RE = re.compile(r"^\$\w+\s*=\s*")


def _is_rename_script(path: str) -> bool:
    return path.replace("\\", "/").lower().endswith(SCRIPT_TAIL)


def _invokes_rename_script(segment: str) -> bool:
    tokens = tokenize_command(ASSIGNMENT_PREFIX_RE.sub("", segment.strip()))
    if not tokens:
        return False
    if basename(tokens[0]) in POWERSHELL_EXES:
        lowered = [t.lower() for t in tokens]
        if "-file" not in lowered:
            return False
        idx = lowered.index("-file")
        return idx + 1 < len(tokens) and _is_rename_script(tokens[idx + 1])
    return _is_rename_script(tokens[0])


def approves(command: str) -> bool:
    if not command or not command.strip():
        return False
    if "$(" in command or "`" in command or ">" in command:
        return False
    segments = [s.strip() for s in split_command_segments(command) if s.strip()]
    segments = [s for s in segments if not BARE_ASSIGNMENT_RE.match(s)]
    return bool(segments) and all(_invokes_rename_script(s) for s in segments)


def main() -> None:
    command = (read_payload().get("tool_input") or {}).get("command", "") or ""
    if approves(command):
        sys.stdout.write(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "allow",
                "permissionDecisionReason": "Auto-approved: /close rename helper",
            }
        }))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[approve-rename] hook error, making no decision: {e}\n")
        sys.exit(0)
