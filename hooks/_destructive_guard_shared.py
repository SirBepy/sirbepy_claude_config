"""Tokenizing primitives shared by destructive-command-guard.py's concern
modules (todo 911 split): statement/segment splitting, quote-aware
splitting, and the leading-prefix stripping every matcher builds on.
"""

import re

from _hooklib import HEREDOC_BODY_RE

# Statement split (no pipe): used only where a pipe must stay intact, i.e.
# pipe_to_shell (the pipe IS the thing being matched) and the SQL rules
# (piping SQL output elsewhere doesn't change whether the SQL itself ran).
STATEMENT_SPLIT_RE = re.compile(r"&&|\|\||;")
# Segment split (pipe included): used by every verb-anchored rule below, so
# a verb after a pipe is still checked as its own command position. Newlines
# split too: a multi-line PowerShell script has no && between statements.
SEGMENT_SPLIT_RE = re.compile(r"\|\||&&|[;|\n]")
LEADING_SUDO_RE = re.compile(r"^sudo\s+", re.IGNORECASE)
LEADING_ENV_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*\s+")
# Wrappers that run another command as their argument, so the real verb sits
# behind them: `xargs -I{} rm -rf ~` was ALLOWED before this list existed.
# PowerShell may put any flags (including value-taking ones like
# `-ExecutionPolicy Bypass`) before `-Command`/`-c`, so it skips whole tokens
# lazily up to the first one; `-File` runs a script and is not a wrapper.
LEADING_WRAPPER_RE = re.compile(
    r"^(xargs(\s+-\S+)*|env|time|nohup|nice(\s+-n\s*-?\d+)?|command|(sh|bash|zsh|dash)\s+-c"
    r"|(powershell|pwsh)(\.exe)?(\s+\S+)*?\s+-(command|c))\s+",
    re.IGNORECASE,
)

# todo 775: bare `git stash` defaults to `push`, so only the read/replay
# subcommands are exempt from the shared-checkout sweep check. Needed by
# both the git-force/reset concern (match_git_stash_push) and the peer-logic
# concern (stash_pathspec_args/stash_swept_files), so it lives here.
GIT_STASH_ANCHOR_RE = re.compile(r"^git\s+(?:-[^\s]+\s+)*stash\b", re.IGNORECASE)
GIT_STASH_SAFE_SUBCMD_RE = re.compile(
    r"^git\s+(?:-[^\s]+\s+)*stash\s+(list|show|pop|apply|drop|clear|branch)\b", re.IGNORECASE)


def strip_heredoc_bodies(command: str) -> str:
    """Collapse each heredoc, from its operator through the closing
    delimiter line, to a single inert placeholder - before any statement or
    segment split runs. A heredoc body is data piped to the preceding
    command's stdin, never executed as shell text, so a verb inside it is
    never at command position (todo 982 step 3: a python heredoc listing
    publish-verb strings as test data was denied as a real `npm publish`).
    Must run first, as a pre-pass on the raw string: a heredoc's own quote
    pair (`<<'EOF'`) would otherwise desync split_outside_quotes's quote-state
    tracker, which has no concept of heredocs. Both tag forms strip, since
    this guard's anchors only care about position.
    """
    return HEREDOC_BODY_RE.sub("<<HEREDOC>>", command)


def split_statements(command: str) -> list:
    return STATEMENT_SPLIT_RE.split(strip_heredoc_bodies(command))


def split_outside_quotes(command: str) -> list:
    """Split on ; && || | and newline, but only OUTSIDE quoted spans.

    A plain split chops a quoted alternation into fake command positions:
    `grep -E "^(a|mkfs|b)"` became a segment beginning `mkfs` and was denied.
    Heredoc bodies are stripped before this split runs (see
    strip_heredoc_bodies) for the same reason: an unquoted body's own `\\n`s
    are not real statement breaks either.
    """
    command = strip_heredoc_bodies(command)
    parts, buf = [], []
    quote = None
    i = 0
    while i < len(command):
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < len(command):
                buf.append(command[i + 1])
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch in (";", "\n"):
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        if ch == "|":
            if command[i:i + 2] == "||":
                i += 2
            else:
                i += 1
            parts.append("".join(buf))
            buf = []
            continue
        if command[i:i + 2] == "&&":
            parts.append("".join(buf))
            buf = []
            i += 2
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


def verb_segments(command: str):
    """Yield each command segment with a leading sudo/env-assignment prefix
    stripped and quote CHARACTERS deleted (not quoted spans masked), so a
    verb regex anchored with ^ matches only a real invocation position and
    `rm -rf "$HOME"` still exposes $HOME to the target pattern.
    """
    for segment in split_outside_quotes(command):
        s = _strip_leading_prefixes(segment.strip())
        # Second pass after the quotes go: `powershell "-Command" "..."` only
        # exposes its wrapper once its flag name is unquoted.
        yield _strip_leading_prefixes(s.replace("'", "").replace('"', ""))


def _strip_leading_prefixes(s: str) -> str:
    while True:
        m = LEADING_SUDO_RE.match(s) or LEADING_ENV_RE.match(s) or LEADING_WRAPPER_RE.match(s)
        if not m:
            return s
        s = s[m.end():]
