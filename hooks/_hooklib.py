"""Shared scaffold for the PreToolUse guard hooks (commit/pr/shell-content-
write/package-manager/flutter-workdir guards).

Only extracts pieces verified byte-identical across the guards. `deny()`
takes an optional suffix so shell-content-write-guard's extra "use Write
instead" tail is representable without duplicating the function.

Callers import this via a loud try/except (see any guard's top few lines):
a broken/missing _hooklib must block hard, not let every guard go quiet.

dev-backend-guard.py's matcher (`^(Bash|PowerShell)$`) is broad: a broken
symbol here blocks every Bash/PowerShell call in every session (todo 850).
Locked out? Edit/Write tool calls bypass that matcher, so fix this file (or
remove the guard's settings.json entry) without needing a shell.
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


def git_repo_root(path) -> str | None:
    """Git toplevel containing `path`, or None if `path` doesn't exist,
    isn't inside a repo, or git fails/times out. Shared resolver (todo 874)
    so a timeout bump or a failure-mode fix lands once for every caller.
    """
    path = str(path)
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


def iter_turn_tool_uses(transcript_path: str):
    """Yield (name, input) for tool_use blocks in assistant entries after the
    most recent REAL user entry (not a tool_result), an approximation of
    "this turn"."""
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
        if e.get("type") == "user" and not is_tool_result_entry(e):
            last_user_idx = i
    for e in entries[last_user_idx + 1:]:
        if e.get("type") != "assistant":
            continue
        content = (e.get("message", {}) or {}).get("content", []) or []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_use":
                yield block.get("name") or "", (block.get("input") or {})
