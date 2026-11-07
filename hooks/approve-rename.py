"""PreToolUse hook (PowerShell): auto-approve /close's rename helper.

Allows a PowerShell call only when EVERY statement in it invokes
`skills/close/rename-session.ps1` in one strict shape: the script itself
(directly, via the `&` call operator, or as the right side of a `$var = ...`
assignment), or `powershell|pwsh [-NoProfile] [-NonInteractive] [-NoLogo]
[-ExecutionPolicy Bypass] -File <script>`. After the script come only named
arguments (`-Name`) with plain quoted or bare values.
The hook it replaces (skills/close/approve-rename.ps1) allowed any command
whose text merely contained the file name, so `Remove-Item x; rename-session.ps1`
and a trailing `# rename-session.ps1` comment both rode the approval, and it
cold-started a PowerShell process on every PowerShell call.

Stays out of the way (no decision, normal permission flow) on anything it
does not recognise, and on any error. A parenthesis, brace, backtick, redirect,
`@` or `$` anywhere but the script path disqualifies it (so a chat name like
"Fix (urgent)" gets the normal permission prompt): those can run or write
something the statement split cannot see. A typographic quote disqualifies it
too: PowerShell reads U+2018/2019/201A/201B/201C/201D/201E as quotes, but the
statement split tracks only ASCII ones, so `'a<U+2019>; New-Item x; <U+2018>b'`
would look like one harmless string. Any token before `-File` that is not a
known switch (a positional script, an abbreviation such as `-f`) is a command
PowerShell runs first, so it disqualifies the call. Only the script under this
user's home counts, never a same-named file elsewhere, and the PowerShell
executable must be a bare name, never a path.
"""

import json
import re
import shlex
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    import _hookboot  # retries a shared module another session is mid-way through writing
    from _hooklib import read_payload, split_command_segments, strip_quotes
except Exception as e:
    sys.stderr.write(f"[approve-rename] cannot import _hooklib ({e}); making no decision.\n")
    sys.exit(0)

HOME = Path.home().as_posix().lower()
# Only the real script under this user's home counts: a same-named script in
# any other directory is attacker-chosen code.
CANONICAL_SCRIPT = HOME + "/.claude/skills/close/rename-session.ps1"
HOME_SPELLINGS = ("~", "$env:userprofile", "$home", "%userprofile%")
POWERSHELL_EXES = {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}
# Switches that may precede -File. Anything else there (-Command, -f, a bare
# word) either runs other code or is a command PowerShell executes itself.
SAFE_SWITCHES = {"-noprofile", "-noninteractive", "-nologo"}

BARE_ASSIGNMENT_RE = re.compile(r"^\$\w+\s*=\s*$")
ASSIGNMENT_PREFIX_RE = re.compile(r"^\$\w+\s*=\s*")
ARG_NAME_RE = re.compile(r"^-[A-Za-z]\w*$")
ARG_VALUE_RE = re.compile(r"""^(?:'[^'"`$@]*'|"[^'"`$@]*"|[\w.:/\\-]+)$""")
# Never legitimate in this helper's command line, wherever they sit.
FORBIDDEN_CHARS = "`>(){}\r@<"
# U+2018-U+201F covers every typographic single and double quote PowerShell
# treats as a quote; the guillemets are rejected on the same grounds.
FORBIDDEN_QUOTE_RANGES = ((0x2018, 0x201F), (0x00AB, 0x00AB), (0x00BB, 0x00BB), (0x2039, 0x203A))


def _is_rename_script(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    for spelling in HOME_SPELLINGS:
        if normalized.startswith(spelling + "/"):
            normalized = HOME + normalized[len(spelling):]
            break
    return normalized == CANONICAL_SCRIPT


def _has_typographic_quote(command: str) -> bool:
    return any(lo <= ord(c) <= hi for c in command for lo, hi in FORBIDDEN_QUOTE_RANGES)


def _plain_named_args(args: list[str]) -> bool:
    """Only `-Name` switches, each optionally followed by one plain value."""
    i = 0
    while i < len(args):
        if not ARG_NAME_RE.match(args[i]):
            return False
        i += 1
        if i < len(args) and not ARG_NAME_RE.match(args[i]):
            if not ARG_VALUE_RE.match(args[i]):
                return False
            i += 1
    return True


def _invokes_rename_script(segment: str) -> bool:
    try:
        raw = shlex.split(ASSIGNMENT_PREFIX_RE.sub("", segment.strip()), posix=False)
    except ValueError:
        return False
    if raw and raw[0] == "&":
        raw = raw[1:]
    if not raw:
        return False
    if strip_quotes(raw[0]).lower() in POWERSHELL_EXES:
        i = 1
        while i < len(raw):
            token = raw[i].lower()
            if token in SAFE_SWITCHES:
                i += 1
            elif token == "-executionpolicy" and i + 1 < len(raw) and raw[i + 1].lower() == "bypass":
                i += 2
            else:
                break
        if i + 1 >= len(raw) or raw[i].lower() != "-file":
            return False
        script, args = raw[i + 1], raw[i + 2:]
    else:
        script, args = raw[0], raw[1:]
    return _is_rename_script(strip_quotes(script)) and _plain_named_args(args)


def approves(command: str) -> bool:
    if not command or not command.strip():
        return False
    # Any expression syntax can run code the statement split cannot see.
    # A bare \r separates PowerShell statements but not the segment splitter's.
    if any(c in command for c in FORBIDDEN_CHARS) or _has_typographic_quote(command):
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
