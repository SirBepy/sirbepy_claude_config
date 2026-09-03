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

`git show <ref>:<path> > <scratch>` writes git's own blob bytes, not
shell-authored content, so the BOM rationale above never reaches it
(todo 792). Corpus check against 62,270 unique commands harvested from
this machine's transcripts (C:\\tmp\\p2-corpus, 2026-09-04): ~104 unique
commands match a bare git-blob redirect, nearly all diffing a pre-refactor
version into a scratch path outside the repo; zero were a disguised
config/authored-content write. Carved out narrowly below: bare `git show`/
`git cat-file` with no pipes or substitutions, redirecting `>` (never
`>>`) to a path outside the current repo.
"""

import re
import subprocess
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
# ".session-markers" covers /commit's session marker, split into its own
# directory from ".commit-marker*" by todo 341 (2026-08-16).
MARKER_HINTS = (".commit-marker", ".pr-marker", ".session-markers")

CONTENT_CMDLET_RE = re.compile(r"\b(Set-Content|Out-File|Add-Content)\b", re.IGNORECASE)
TEE_RE = re.compile(r"\btee\b\s+(?:-a\s+)?(\S+)", re.IGNORECASE)
# `=>`, `->`, `!>`, `<>` are operators, never redirects, regardless of shell dialect
# (Dart/JS arrows, comparisons); `>=` is the trailing-side twin, so a lone `>` right
# before `=` is excluded too (todo 476).
REDIRECT_RE = re.compile(r"(?<![=\-!<])(\d)?(>{1,2})(?!=)(&\d)?\s*(\S*)")

# A quoted-tag heredoc (`<<'TAG'`, `<<"TAG"`, `<<-'TAG'`) passes its body to the
# command's stdin byte-for-byte, no shell interpretation, so it is stripped before
# any other scan runs (todo 476). An unquoted `<<TAG` still expands `$vars`, so it
# stays in scope for the other checks.
HEREDOC_RE = re.compile(r"<<-?\s*(['\"])(\w+)\1[^\n]*\n.*?^[ \t]*\2[ \t]*$", re.MULTILINE | re.DOTALL)


def strip_heredocs(command: str) -> str:
    return HEREDOC_RE.sub("HEREDOC_BODY", command)


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


# Splits a command into statements the same way COMMAND_START_RE recognizes
# a new command start, so the git-blob-read check only ever inspects the
# statement immediately feeding the redirect, never an earlier one.
STATEMENT_BOUNDARY_RE = re.compile(r"[|;&(){\n]")

# Bare `git show`/`git cat-file -p|blob <ref>:<path>`, nothing else: no `$()`,
# backtick, pipe, or extra redirect in the segment, so nothing but git's own
# blob bytes can reach the target this statement feeds.
GIT_BLOB_READ_RE = re.compile(
    r"^\s*git\s+(?:show|cat-file\s+(?:-p|blob))\b[^|;&$`<>\n]*\s\S+:\S+\s*$"
)

GIT_TIMEOUT_SECONDS = 5


def _statement_before(masked: str, idx: int) -> str:
    bounds = [m.end() for m in STATEMENT_BOUNDARY_RE.finditer(masked[:idx])]
    start = bounds[-1] if bounds else 0
    return masked[start:idx]


def _repo_root(cwd: str) -> Path | None:
    if not cwd:
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        return Path(proc.stdout.strip()).resolve()
    except OSError:
        return None


def _target_outside_repo(target: str, cwd: str) -> bool:
    """True only when `target` resolves outside the repo containing `cwd`.
    An unresolvable repo root counts as "not proven outside" (fail closed):
    the carve-out below only fires when this is True.
    """
    repo_root = _repo_root(cwd)
    if repo_root is None:
        return False
    try:
        target_path = Path(target)
        if not target_path.is_absolute():
            target_path = Path(cwd) / target_path
        target_path = target_path.resolve()
    except OSError:
        return False
    return target_path != repo_root and repo_root not in target_path.parents


def is_git_blob_redirect(masked: str, idx: int, fd: str | None, op: str, target: str, cwd: str) -> bool:
    """True when the `>` at `idx` is fed solely by a bare git blob read and
    lands outside the current repo (todo 792). `fd` must be absent (no `2>`
    stderr capture) and `op` a single `>` (never `>>`, which could blend
    blob bytes into an existing file's content).
    """
    if fd or op != ">":
        return False
    if not GIT_BLOB_READ_RE.match(_statement_before(masked, idx)):
        return False
    return _target_outside_repo(target, cwd)


def deny(reason: str) -> None:
    _lib_deny(
        "[shell-content-write-guard] " + reason,
        suffix=(
            " Use the Write tool instead, or "
            "[System.IO.File]::WriteAllText($path, $text) when a script "
            "genuinely must write through the shell."
        ),
    )


def _combined_quote_re(dquote_re: re.Pattern) -> re.Pattern:
    return re.compile(
        "|".join(p.pattern for p in (HERESTRING_RE, dquote_re, SQUOTE_RE)),
        re.DOTALL,
    )


def mask_quoted(command: str, dquote_re: re.Pattern) -> str:
    """Replace quoted/here-string regions with a fixed no-symbol token so
    a `>` or `-` inside string content can never look like an operator,
    while a quoted redirect target still counts as a present token.

    One combined alternation, scanned left to right in a single pass:
    whichever quote character opens first consumes its own matching close
    atomically, so a `"` living inside a single-quoted span (or vice versa)
    can never pair across the other quote type's boundary. Three
    independent sequential passes (todo 845) let an odd quote count inside
    one span pair with a stray quote elsewhere in the command, masking a
    real `>` in between.
    """
    return _combined_quote_re(dquote_re).sub("QSTR", command)


# Chars that legitimately precede a new command/statement. A cmdlet match is
# only treated as an invocation when it sits right after one of these (or at
# the very start), so `grep 'Set-Content'` (inside a masked-out string) or
# prose naming the cmdlet never counts, only actual command position does.
COMMAND_START_RE = re.compile(r"(?:^|[|;&(){\n])\s*$")


def is_command_position(masked: str, idx: int) -> bool:
    return bool(COMMAND_START_RE.search(masked[:idx]))


def _has_iex(masked: str) -> bool:
    return any(is_command_position(masked, m.start()) for m in IEX_RE.finditer(masked))


def _check_masked(masked: str, cwd: str) -> str | None:
    for m in CONTENT_CMDLET_RE.finditer(masked):
        if is_command_position(masked, m.start()):
            return f"PowerShell content-write cmdlet `{m.group(1)}` writes file content through the shell."

    tee = TEE_RE.search(masked)
    if tee and clean_target(tee.group(1)).lower() not in NULL_TARGETS:
        return "`tee` writes file content through the shell."

    for m in REDIRECT_RE.finditer(masked):
        fd, op, amp, target = m.groups()
        if amp:
            continue  # fd duplication like 2>&1, not a file write
        target_clean = clean_target(target)
        if target_clean.lower() in NULL_TARGETS:
            continue
        if is_git_blob_redirect(masked, m.start(), fd, op, target_clean, cwd):
            continue
        return f"`{op}` redirect writes file content to `{target_clean or '(quoted target)'}` through the shell."

    return None


def find_violation(command: str, cwd: str = "") -> str | None:
    lowered = command.lower()
    if any(hint in lowered for hint in MARKER_HINTS):
        return None

    command = strip_heredocs(command)
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

    return _check_masked(masked_bash, cwd) or _check_masked(masked_pwsh, cwd)


def main() -> None:
    payload = read_payload()
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not command.strip():
        sys.exit(0)

    cwd = payload.get("cwd") or ""
    reason = find_violation(command, cwd)
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
