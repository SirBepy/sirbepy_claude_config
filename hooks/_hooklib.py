"""Shared scaffold for the PreToolUse guard hooks (commit/pr/shell-content-
write/package-manager/flutter-workdir guards).

Only extracts pieces verified byte-identical across the guards. `deny()`
takes an optional suffix so shell-content-write-guard's extra "use Write
instead" tail is representable without duplicating the function.

Callers import this via a loud try/except (see any guard's top few lines):
a broken/missing _hooklib must block hard, not let every guard go quiet.
Each caller first does `import _hookboot`, which retries a half-written
_hooklib once after a short sleep (a session mid-edit clears well inside it).

dev-backend-guard.py's matcher (`^(Bash|PowerShell)$`) is broad: a broken
symbol here blocks every Bash/PowerShell call in every session (todo 850).
There is NO in-session escape: the Write/Edit guards (secret-write-guard.py
and others) fail closed on the same import, so a genuinely broken file blocks
Bash, PowerShell, Write and Edit together. Repair it from a terminal outside
Claude Code (`git -C ~/.claude checkout -- hooks/_hooklib.py`), and write this
file in ONE Write call so no reader ever sees it half-finished.
"""

import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

# Shared across all six guards; verified byte-identical before the move (todo 380).
FRESHNESS_SECONDS = 120
OUTBOUND_MARKER_GLOB = ".outbound-marker*"

# Shared by every guard that resolves a git root (todo 874: was three
# separate GIT_TIMEOUT_SECONDS=10 constants and two repo_root() copies).
GIT_TIMEOUT_SECONDS = 10

# Per-platform claim-bearing field names (todo 381). A write to one of these fields
# asserts something about the code; a state move or self-assign does not, so it stays
# ungated. Kept as its own mapping, never merged into the freshness constants above -
# each guard derives its own matcher (dict-key check or regex) from its own tuple here.
CLAIM_FIELDS = {
    "shortcut": ("name", "description", "text"),
    "linear": ("title", "description"),
}


def read_payload() -> dict:
    """Read stdin, strip a leading BOM, parse as JSON.

    Raises on genuinely malformed input - never substitutes a silent
    default, so a parse failure surfaces through the caller's own
    fail-open/fail-loud handling instead of vanishing here.
    """
    raw = sys.stdin.read()
    return json.loads(raw.lstrip("﻿") or "{}")


def deny(reason: str, suffix: str = "") -> None:
    sys.stderr.write(reason + suffix + "\n")
    sys.exit(2)


def allow_with_warning(reason: str) -> None:
    """Advisory PreToolUse 'allow' decision carrying `reason`: JSON on
    stdout, exit 0. The tool call proceeds either way - unlike ask()/deny(),
    this only surfaces `reason` to the transcript.
    """
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def ask(reason: str) -> None:
    """Emit an advisory PreToolUse 'ask' decision: JSON on stdout, exit 0.

    Not exit 2 - that is deny()'s hard-block path. The harness only reads
    permissionDecision:"ask" from stdout when the process exits 0.
    """
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def basename(tok: str) -> str:
    """Last path segment of `tok`, case-folded. The rstrip handles a
    trailing slash ("foo/" -> "foo", not "") - dev-server-guard's two call
    sites already lower() the result too, so folding case here is a no-op
    for them, not a behaviour change.
    """
    return re.split(r"[\\/]", tok.rstrip("\\/"))[-1].lower()


def is_agent_call(payload: dict) -> bool:
    """True when this hook call came from a dispatched agent, not the
    top-level orchestrator session. `agent_id` is present in the payload if,
    and only if, the call comes from a dispatched agent (probed 2026-09-10,
    re-verified 2026-09-11)."""
    return bool(payload.get("agent_id"))


def is_program(tok: str, name: str) -> bool:
    """True when `tok` launches the program `name`, however it is spelled:
    `git`, `git.exe`, or a full path to either. `name` is lowercase."""
    return basename(tok).removesuffix(".exe") == name


# Chars that legitimately precede a new command/statement. A regex match is
# only treated as a real invocation when it sits right after one of these
# (or at the very start), so a keyword inside a quoted string or prose never
# counts. Was byte-identical in cargo-test-pipe-guard.py/shell-content-write-guard.py.
COMMAND_START_RE = re.compile(r"(?:^|[|;&(){\n])\s*$")


def is_command_position(text: str, idx: int) -> bool:
    return bool(COMMAND_START_RE.search(text[:idx]))


def strip_quotes(tok: str) -> str:
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ("\"", "'"):
        return tok[1:-1]
    return tok


def tokenize_command(command: str) -> list[str]:
    """Shell-tokenize a whole command (todo 893). posix=False keeps Windows
    backslash paths intact; quotes are stripped manually since posix=False
    otherwise leaves them attached. For dev-server-guard/package-manager-
    guard, both already documented as failing open on any hook error: an
    unbalanced-quote ValueError falls back to a naive whitespace split
    rather than an empty list, so pattern matching still gets a shot.
    """
    try:
        return [strip_quotes(t) for t in shlex.split(command, posix=False)]
    except ValueError:
        return command.split()


_LINE_CONTINUATION_RE = re.compile(r"[\\`]\r?\n[ \t]*")


def join_line_continuations(command: str) -> str:
    """Join bash `\\<newline>` and PowerShell `<backtick><newline>` continuations
    into one space, so `git \\<newline>commit` reads as `git commit`. Joining can
    only merge words, never hide one."""
    return _LINE_CONTINUATION_RE.sub(" ", command)


def split_shell_words(command: str) -> list[str]:
    """shlex.split(posix=True) that keeps the backslashes of an unquoted Windows
    path (`C:\\Git\\git.exe`, `.\\git.exe`), which plain posix mode eats, and
    joins line continuations first. A backslash before whitespace or a quote
    stays an escape, and quoted text is untouched. Raises ValueError on an
    unbalanced quote, like shlex."""
    command = join_line_continuations(command)
    out: list[str] = []
    quote = None
    i = 0
    while i < len(command):
        ch = command[i]
        if quote:
            out.append(ch)
            if quote == '"' and ch == "\\" and command[i + 1:i + 2] in ('"', "\\"):
                out.append(command[i + 1])
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "\\" and command[i + 1:i + 2] and not command[i + 1].isspace() and command[i + 1] not in "\"'":
            out.append("\\\\")
        else:
            out.append(ch)
        i += 1
    return shlex.split("".join(out), posix=True)


def _space_operators(command: str) -> str:
    """Put spaces around every unquoted `;`, `&&`, `||`, `&`, `|`, `(` and `)`, so
    `cd x&&git commit` and `echo a;git push` split into the words a shell runs
    (shlex keeps them glued into `x&&git`). Quoted text is left alone."""
    out: list[str] = []
    quote = None
    i = 0
    while i < len(command):
        ch = command[i]
        if quote:
            out.append(ch)
            if quote == '"' and ch == "\\" and command[i + 1:i + 2] in ('"', "\\"):
                out.append(command[i + 1])
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch in ";&|()":
            run = ch
            if ch in "&|":
                while command[i + 1:i + 2] == ch:
                    run += ch
                    i += 1
            out.append(f" {run} ")
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def shell_word_variants(command: str) -> list[list[str]]:
    """Every plausible word split of `command`: the backslash-keeping one
    (`C:\\Git\\git.exe`) and the bash one (`g\\it` is `git`, `\\commit` is
    `commit`). The two disagree only on an unquoted backslash, and a guard
    cannot know whether the command runs in bash or PowerShell, so it checks
    both. Raises ValueError only when neither split parses."""
    variants: list[list[str]] = []
    command = _space_operators(command)
    for split in (split_shell_words, lambda c: shlex.split(join_line_continuations(c), posix=True)):
        try:
            words = split(command)
        except ValueError:
            continue
        if words not in variants:
            variants.append(words)
    if not variants:
        raise ValueError("unbalanced quotes")
    return variants


def command_word(tok: str) -> str:
    """`tok` without a leading subshell or substitution opener (`(git`, `$(git`,
    a backtick) and without a statement terminator glued to its end (`commit;`,
    `push&&echo`, `commit|cat`), which shlex keeps inside the word. Use it where a
    token is compared with a program or subcommand name."""
    return re.split(r"[;&|)]", tok.lstrip("(`$"))[0]


def flatten_tokens(tokens: list[str]) -> list[str]:
    """PowerShell `-ArgumentList "a","b","c"` collapses to one shlex token
    when there's no whitespace between the commas; split those back apart.
    """
    out: list[str] = []
    for tok in tokens:
        for piece in tok.split(","):
            piece = strip_quotes(piece.strip())
            if piece:
                out.append(piece)
    return out


def tokenize_segment(segment: str) -> list[str]:
    """Shell-tokenize one chain-split segment (todo 893), for the two HARD
    BLOCK guards (dev-backend-guard, flutter-workdir-guard). Unlike
    tokenize_command, the ValueError fallback must never be an empty list:
    both callers skip a segment outright when it has no tokens, so an empty
    result on unbalanced quotes would smuggle a blocked command straight
    past the hard-block check it exists to enforce. flutter-workdir-guard
    returned [] here before this fix; dev-backend-guard's whitespace-split
    behaviour is the one both guards now share.
    """
    try:
        return flatten_tokens(shlex.split(segment, posix=False))
    except ValueError:
        return segment.split()


_MSYS_DRIVE_RE = re.compile(r"^/([A-Za-z])(/.*)?$")


def normalize_msys_path(path) -> str:
    """Git Bash spells a drive path `/c/Users/x`; native Windows Python and git
    read that as a `c` folder at the root of the current drive, which does not exist. Rewrites
    it to `C:/Users/x` on Windows so a `cd /c/...` in a Bash-tool command
    resolves to the repo it really targets. Any other path is returned as is."""
    path = str(path)
    m = _MSYS_DRIVE_RE.match(path) if os.name == "nt" else None
    return f"{m.group(1).upper()}:{m.group(2) or '/'}" if m else path


def git_repo_root(path) -> str | None:
    """Git toplevel containing `path`, or None if `path` doesn't exist,
    isn't inside a repo, or git fails/times out. Shared resolver (todo 874)
    so a timeout bump or a failure-mode fix lands once for every caller.
    A Git Bash `/c/...` drive path is accepted (see normalize_msys_path).
    """
    path = normalize_msys_path(path)
    if not path or not os.path.isdir(path):
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", path, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def git_common_dir(path) -> str | None:
    """Absolute git common dir (the MAIN checkout's `.git`) containing
    `path`, or None if `path` doesn't exist, isn't inside a repo, or git
    fails/times out. In a linked worktree this resolves to the main
    checkout's `.git`, distinct from the worktree's own `--git-dir`
    (`<main>/.git/worktrees/<name>`); in the main checkout itself it is the
    same directory `git_repo_root` resolves to, one level deeper. Verified
    empirically (2026-09-10): a linked worktree prints an absolute path
    here, the main checkout prints a bare relative `.git`, so the relative
    case is joined onto `path` before resolving. Used to tell a session's
    own linked worktree apart from an unrelated repo without matching on
    directory names (todo 966).
    """
    path = normalize_msys_path(path)
    if not path or not os.path.isdir(path):
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", path, "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    out = proc.stdout.strip()
    if not out:
        return None
    common = Path(out)
    if not common.is_absolute():
        common = Path(path) / common
    try:
        return str(common.resolve())
    except OSError:
        return str(common)


def oldest_fresh_marker(
    marker_dir: Path,
    glob_pattern: str,
    freshness_seconds: int,
    exclude_prefix: str | None = None,
) -> Path | None:
    """Oldest marker in `marker_dir` matching `glob_pattern` still within
    the freshness window, or None. Oldest-first so a session that's been
    waiting longest gets consumed first, leaving newer (likely concurrent-
    session) markers alone. `exclude_prefix` skips names like a session
    marker prefix that must never be consumed here.
    """
    now = time.time()
    candidates = []
    for path in marker_dir.glob(glob_pattern):
        if exclude_prefix and path.name.startswith(exclude_prefix):
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if now - mtime <= freshness_seconds:
            candidates.append((mtime, path))
    if not candidates:
        return None
    candidates.sort(key=lambda pair: pair[0])
    return candidates[0][1]


def consume_fresh_marker(
    marker_dir: Path,
    glob_pattern: str,
    freshness_seconds: int,
    exclude_prefix: str | None = None,
) -> bool:
    """Find the oldest fresh marker and delete it. Returns True (allow) if one
    existed, False (fall through to deny) otherwise.

    The unlink's OSError is swallowed on purpose: a concurrent session may
    have already consumed the same marker file, and losing that race is not
    an error, it just means this call falls through to the deny path below.
    """
    marker = oldest_fresh_marker(marker_dir, glob_pattern, freshness_seconds, exclude_prefix)
    if marker is None:
        return False
    try:
        marker.unlink()
    except OSError:
        pass
    return True


def is_tool_result_entry(entry: dict) -> bool:
    """A tool_result is wrapped in a `type: user` entry in this transcript
    format, distinguishable from a real human prompt only by content shape:
    its `message.content` is a list of blocks carrying `type: tool_result`."""
    if entry.get("type") != "user":
        return False
    content = (entry.get("message", {}) or {}).get("content")
    if not isinstance(content, list):
        return False
    return any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content)


def _entry_text(entry: dict) -> str:
    """Flatten a transcript entry's `message.content` to plain text,
    whether it is a bare string or a list of blocks (text blocks only -
    tool_result/tool_use blocks carry no `text` key and are skipped)."""
    content = (entry.get("message", {}) or {}).get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(
            b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"
        )
    return ""


# Prefixes marking a `type: user` transcript entry the harness injected
# mid-turn rather than a human/queued prompt: a cross-session subagent
# hand-back relay or a background-task completion notification. Neither
# starts a new human turn, so a turn-boundary scan must look past one rather
# than treating it as "this turn" starting here (todo 1081 - a send_message
# made before one of these arrived was getting hidden, falsely tripping the
# silent-turn counter in send-message-stop-guard.py even though the turn DID
# send). `<agent-message from="...">` is the same hand-back marker
# hooks/_outbound_verify_transcript.py's AGENT_MESSAGE_RE already parses,
# confirmed against a real transcript (session 6a91451f, lines 392 and 603).
# Two prefixes stay boundaries on purpose. "Stop hook feedback:" does:
# Stop hooks that never check stop_hook_active (ui-screenshot-reminder.py)
# rely on it closing the window, or an edit before it re-blocks every Stop,
# and a stale send_message before it must not keep re-triggering the
# send-message guard's content checks. The `[daemon-meta]` peer-relay prefix
# does too: the Stop guard's relay exemption (todo 410/1032) depends on a
# relay-only turn counting as its own turn.
_INJECTED_USER_ENTRY_RE = re.compile(
    r"^(?:Another Claude session sent a message:\s*<agent-message\b"
    r"|<task-notification>)"
)


def is_injected_user_entry(entry: dict) -> bool:
    """True if a `type: user` entry is a harness-injected mid-turn
    notification (see _INJECTED_USER_ENTRY_RE) rather than a real human or
    queued prompt. Checked alongside `is_tool_result_entry` wherever a turn
    boundary is scanned - neither alone covers both non-boundary shapes."""
    if entry.get("type") != "user":
        return False
    return bool(_INJECTED_USER_ENTRY_RE.match(_entry_text(entry).lstrip()))


def iter_turn_tool_uses(transcript_path: str):
    """Yield (name, input) for tool_use blocks in assistant entries after the
    most recent REAL user entry (not a tool_result, not a harness-injected
    mid-turn notification), an approximation of "this turn"."""
    path = Path(transcript_path)
    if not path.exists():
        return
    entries = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    last_user_idx = -1
    for i, e in enumerate(entries):
        if e.get("type") == "user" and not is_tool_result_entry(e) and not is_injected_user_entry(e):
            last_user_idx = i
    for e in entries[last_user_idx + 1:]:
        if e.get("type") != "assistant":
            continue
        content = (e.get("message", {}) or {}).get("content", []) or []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield block.get("name") or "", (block.get("input") or {})


# A heredoc (quoted or bare tag) or a PowerShell here-string body is data, not commands.
# The quoted-tag-only variant serves shell-content-write-guard.py: an unquoted body still
# expands $vars, so that guard keeps it in scope. One template, so a fix lands in both.
# Only `<<-` lets the closing tag line be indented; under plain `<<` an indented tag is body text.
_HEREDOC_TEMPLATE = r"<<(-)?[ \t]*({quote})(\w+)\2[^\n]*\n(?:.*?\n)??(?(1)[ \t]*)\3[ \t]*(?=\n|$)"
HEREDOC_BODY_RE = re.compile(_HEREDOC_TEMPLATE.format(quote="['\"]?"), re.DOTALL)
QUOTED_HEREDOC_BODY_RE = re.compile(_HEREDOC_TEMPLATE.format(quote="['\"]"), re.DOTALL)
HERESTRING_BODY_RE = re.compile(r"@(['\"])\r?\n.*?\r?\n\1@", re.DOTALL)


def split_command_segments(command: str) -> list[str]:
    """Statements and pipeline segments of a shell command, split on ; | & and
    newlines that sit outside quotes, with heredoc and here-string bodies
    dropped first so text inside them never reads as a command.

    There is no backslash or backtick escape handling (PowerShell reads
    "C:\\dir\\" as a closed string), so quotes still open at the end mean the
    scan desynced, e.g. on `echo "a\\" b"; fvm flutter build`. The text then
    falls back to the plain split, which over-splits instead of hiding the
    command after the quote."""
    text = HERESTRING_BODY_RE.sub("", HEREDOC_BODY_RE.sub("", command))
    segments, buf, quote = [], [], None
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch in ";|&\n":
            segments.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if quote:
        return [s for s in re.split(r"[;|&\n]", text) if s.strip()]
    segments.append("".join(buf))
    return [s for s in segments if s.strip()]


# The separators the gate guards have always split on: `&&`, `||`, `;`, newline
# and `|`. A lone `&` is deliberately not one, so `2>&1` stays inside its segment.
_GATE_CHAIN_SPLIT_RE = re.compile(r"&&|\|\||;|\n|\|")


def split_gate_segments(command: str) -> list[str]:
    """Statements and pipeline segments for the fail-closed gate guards: split
    on `&&`, `||`, `;`, newline and `|` that sit outside single or double
    quotes, so a pattern like grep "a|b" or a commit message holding "x; y"
    stays one segment.

    Unlike split_command_segments, heredoc bodies are kept (a body piped into
    `bash` is executed, so a gate must still see it), and a lone `&` is not a
    separator. There is no backslash or backtick escape handling, because
    PowerShell reads "C:\\dir\\" as a closed string; instead, quotes still open
    at the end mean the scan desynced (an escaped quote, a stray apostrophe in
    a heredoc body), so the whole command falls back to the plain split, which
    over-splits and therefore over-gates rather than hiding a later command."""
    command = command or ""
    segments, buf, quote, i = [], [], None, 0
    while i < len(command):
        ch = command[i]
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch in ";|\n":
            segments.append("".join(buf))
            buf = []
        elif ch == "&" and command[i + 1:i + 2] == "&":
            segments.append("".join(buf))
            buf = []
            i += 1
        else:
            buf.append(ch)
        i += 1
    if quote:
        return [s for s in _GATE_CHAIN_SPLIT_RE.split(command) if s.strip()]
    segments.append("".join(buf))
    return [s for s in segments if s.strip()]


# A real shell's `-c`/`-Command` argument is itself a command line.
SHELL_WRAPPER_NAMES = {"bash", "sh", "zsh", "dash", "pwsh", "powershell"}
INLINE_COMMAND_FLAGS = {"-c", "-lc", "-command"}


def with_wrapper_bodies(segments: list[str], depth: int = 0) -> list[str]:
    """`segments` plus, after each segment that runs a shell with `-c` or
    `-Command`, the statements of that quoted argument (nested wrappers up to
    three deep). The quote-aware splits keep such an argument as one token, so
    without this a command inside `bash -c "..."` is invisible."""
    out = []
    for segment in segments:
        out.append(segment)
        if depth >= 3:
            continue
        tokens = tokenize_segment(segment)
        for i in range(1, len(tokens) - 1):
            if tokens[i].lower() in INLINE_COMMAND_FLAGS and any(
                basename(t).removesuffix(".exe") in SHELL_WRAPPER_NAMES for t in tokens[:i]
            ):
                body = strip_quotes(tokens[i + 1])
                out.extend(with_wrapper_bodies(split_command_segments(body), depth + 1))
    return out


# Commands that only print or search the text they are given. A request spelled
# out in their quoted arguments is prose, not a request: `echo "curl -X POST <url>"`.
# This is a deny-list on purpose: anything not named here keeps being read as a
# command that may send a request (a launcher, a script, a quoted exe path).
_DISPLAY_COMMANDS = {
    "echo", "printf", "write-host", "write-output", "write-warning", "write-verbose",
    "write-information", "write-error", "grep", "egrep", "fgrep", "select-string", "sls", "findstr",
}
# Not `rg` (--pre runs a command) and not `git grep` (-O runs a pager command).
_DISPLAY_GIT_SUBCOMMANDS = {"commit", "log", "tag", "notes", "show", "diff", "blame"}
_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_]\w*=")


def _quoted_mask(text: str) -> tuple[list[bool], bool]:
    """(mask, balanced): True for characters inside a single- or double-quoted
    span. No escape handling (PowerShell reads "C:\\dir\\" as a closed string),
    so a quote still open at the end means the mask cannot be trusted."""
    mask, quote = [False] * len(text), None
    for i, ch in enumerate(text):
        if quote:
            mask[i] = True
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            mask[i] = True
    return mask, quote is None


def _command_words(segment: str) -> list[str]:
    """Whitespace words of a statement without a leading call operator or
    `VAR=value` assignments, i.e. starting at the command itself."""
    words = segment.split()
    while words and (words[0] == "&" or _ASSIGNMENT_RE.match(words[0])):
        words.pop(0)
    return words


# The lookahead keeps `>&1.sh` or `>/dev/null.sh` (real file targets) from reading as harmless.
_HARMLESS_REDIRECT_RE = re.compile(r"\d*>&\d(?=\s|$)|\d*>>?\s*(?:/dev/null|\$null)(?=\s|$)")


def _is_display_segment(segment: str) -> bool:
    mask, balanced = _quoted_mask(segment)
    # Unpaired quotes mean the read cannot be trusted; a command substitution runs.
    if not balanced or "$(" in segment or "`" in segment:
        return False
    # Outside quotes, `&` (background), parentheses (a PowerShell subexpression
    # runs), and redirects (a script file written now and run later) all mean the
    # statement does more than print; only a redirect to the null device or an fd is harmless.
    bare = _HARMLESS_REDIRECT_RE.sub(" ", "".join(" " if m else c for c, m in zip(segment, mask)))
    if any(c in bare for c in "&()<>"):
        return False
    words = _command_words(segment)
    if not words:
        return False
    first = basename(words[0]).removesuffix(".exe")
    if first in _DISPLAY_COMMANDS:
        return True
    if first != "git":
        return False
    rest, i = words[1:], 0
    while i < len(rest) and rest[i].startswith("-"):
        i += 2 if rest[i] in ("-C", "-c") else 1
    return i < len(rest) and rest[i] in _DISPLAY_GIT_SUBCOMMANDS


def without_display_segments(command: str) -> str:
    """`command` with the statements that only print or search text removed, so
    a request named in `echo "curl -X POST <url> -d x"` or a commit message is
    not mistaken for one. Anything else stays. A display statement whose output
    is piped onward (`echo "..." | bash`, `| sudo bash`, `| % { iex $_ }`) stays
    too: the next stage may execute it, and no list of executors is complete."""
    out, cursor, stripped = [], 0, False
    for segment in split_gate_segments(command):
        start = command.find(segment, cursor)
        if start < 0:
            return command  # cannot place the statement, so strip nothing
        end = start + len(segment)
        # The pipe may sit after a line break or a continuation backslash.
        after = command[end:].lstrip(" \t\r\n\\")
        piped = after.startswith("|") and not after.startswith("||")
        # A line that continues the previous one (`curl ... \` then `echo -d x`) is an argument, not a statement.
        continued = command[:start].rstrip(" \t\r\n").endswith(("\\", "`"))
        if not (piped or continued) and _is_display_segment(segment):
            # Blank the statement in place so every other statement keeps its
            # separators and line continuations (`curl <url> \` then `-d x`).
            out.append(command[cursor:start] + " " * len(segment))
            stripped = True
        else:
            out.append(command[cursor:end])
        cursor = end
    return "".join(out) + command[cursor:] if stripped else command


# Keep this the LAST statement. _hookboot treats a module without it as a file
# another session is still writing (empty, or cut at a statement boundary, both
# of which import cleanly) and retries instead of letting a hook's
# `from _hooklib import ...` fail on a missing name.
_HOOKLIB_COMPLETE = True
