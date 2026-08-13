"""PreToolUse hook: block writing file CONTENT through the shell.

Fires on Bash/PowerShell tool calls. Windows PowerShell 5.1 prepends a
UTF-8 BOM to Set-Content/Out-File/redirect output even with -Encoding
utf8, which breaks strict parsers (serde_json, gh secret set, TOML/YAML
readers) and silently mangles non-ASCII bytes. Three incidents on record:
gh secret set (2026-07), taskbar-widgets settings.json (2026-08-05), a
mockup HTML file (2026-08-09). Use the Write tool instead, or
[System.IO.File]::WriteAllText($path, $text) when a script must do it.

Detection is regex-based on the raw command string, not a real shell
parser, so it is deliberately conservative: quoted string content is
masked before redirect operators are matched, to avoid tripping on `>`
inside a string, a comparison, or a JS arrow function. Masking runs under
both bash and PowerShell quote-escape rules and blocks if either flags a
hit; iex/Invoke-Expression is special-cased since it evaluates its masked-
out string argument as real code. The /commit skill's own marker write is
allowlisted explicitly. Fails open on error.
"""

import re
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, deny as _lib_deny
except Exception as e:
    sys.stderr.write(f"[shell-content-write-guard] FATAL: cannot import _hooklib ({e}); blocking to avoid silently disabling this guard.\n")
    sys.exit(2)

# Guard-marker writes are the one sanctioned Set-Content: blocking them would
# lock /commit and /create-pr out of their own PreToolUse gates entirely.
MARKER_HINTS = (".commit-marker", ".pr-marker")

CONTENT_CMDLET_RE = re.compile(r"\b(Set-Content|Out-File|Add-Content)\b", re.IGNORECASE)
TEE_RE = re.compile(r"\btee\b\s+(?:-a\s+)?(\S+)", re.IGNORECASE)
REDIRECT_RE = re.compile(r"(?<![=\-])(\d)?(>{1,2})(&\d)?\s*(\S*)")

NULL_TARGETS = {"$null", "/dev/null", "nul", "null", ""}

HERESTRING_RE = re.compile(r"@'.*?'@|@\".*?\"@", re.DOTALL)
# Bash escapes " with \; PowerShell never does (backtick or doubled "" instead). One
# regex masking lets the other dialect's real code hide as "string content", so both
# are checked and either flagging a hit blocks (fail closed).
DQUOTE_RE_BASH = re.compile(r'"(?:[^"\\]|\\.)*"')
DQUOTE_RE_PWSH = re.compile(r'"(?:`.|""|[^"])*"')
SQUOTE_RE = re.compile(r"'[^']*'")
IEX_RE = re.compile(r"\b(iex|Invoke-Expression)\b", re.IGNORECASE)

# \S* in REDIRECT_RE/TEE_RE swallows trailing shell separators glued to the
# target (e.g. `/dev/null;`), so they must be trimmed before NULL_TARGETS.
TRAILING_SEP_RE = re.compile(r"[;&|)]+$")


def clean_target(raw: str) -> str:
    return TRAILING_SEP_RE.sub("", (raw or "").strip("\"'"))


def deny(reason: str) -> None:
    _lib_deny(
        "[shell-content-write-guard] " + reason,
        suffix=(
            " Use the Write tool instead, or "
            "[System.IO.File]::WriteAllText($path, $text) when a script "
            "genuinely must write through the shell."
        ),
    )


def mask_quoted(command: str, dquote_re: re.Pattern) -> str:
    """Replace quoted/here-string regions with a fixed no-symbol token so
    a `>` or `-` inside string content can never look like an operator,
    while a quoted redirect target still counts as a present token.
    """
    masked = HERESTRING_RE.sub("QSTR", command)
    masked = dquote_re.sub("QSTR", masked)
    masked = SQUOTE_RE.sub("QSTR", masked)
    return masked


# Chars that legitimately precede a new command/statement. A cmdlet match is
# only treated as an invocation when it sits right after one of these (or at
# the very start), so `grep 'Set-Content'` (inside a masked-out string) or
# prose naming the cmdlet never counts, only actual command position does.
COMMAND_START_RE = re.compile(r"(?:^|[|;&(){\n])\s*$")


def is_command_position(masked: str, idx: int) -> bool:
    return bool(COMMAND_START_RE.search(masked[:idx]))


def _has_iex(masked: str) -> bool:
    return any(is_command_position(masked, m.start()) for m in IEX_RE.finditer(masked))


def _check_masked(masked: str) -> str | None:
    for m in CONTENT_CMDLET_RE.finditer(masked):
        if is_command_position(masked, m.start()):
            return f"PowerShell content-write cmdlet `{m.group(1)}` writes file content through the shell."

    tee = TEE_RE.search(masked)
    if tee and clean_target(tee.group(1)).lower() not in NULL_TARGETS:
        return "`tee` writes file content through the shell."

    for m in REDIRECT_RE.finditer(masked):
        _fd, op, amp, target = m.groups()
        if amp:
            continue  # fd duplication like 2>&1, not a file write
        target_clean = clean_target(target)
        if target_clean.lower() in NULL_TARGETS:
            continue
        return f"`{op}` redirect writes file content to `{target_clean or '(quoted target)'}` through the shell."

    return None


def find_violation(command: str) -> str | None:
    lowered = command.lower()
    if any(hint in lowered for hint in MARKER_HINTS):
        return None

    masked_bash = mask_quoted(command, DQUOTE_RE_BASH)
    masked_pwsh = mask_quoted(command, DQUOTE_RE_PWSH)

    # iex/Invoke-Expression evaluates its string argument as real code, so a
    # write cmdlet masked away as "just a string" is actually live. Check
    # the raw, unmasked command instead of trusting either masking here.
    if _has_iex(masked_bash) or _has_iex(masked_pwsh):
        m = CONTENT_CMDLET_RE.search(command)
        if m:
            return (
                f"`{m.group(1)}` appears inside a string passed to iex/"
                "Invoke-Expression, which evaluates it as live code."
            )

    return _check_masked(masked_bash) or _check_masked(masked_pwsh)


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not command.strip():
        sys.exit(0)

    reason = find_violation(command)
    if reason:
        deny(reason)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[shell-content-write-guard] hook error, failing open: {e}\n")
        sys.exit(0)
