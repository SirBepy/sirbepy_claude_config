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
import sys
import time
from pathlib import Path

# Shared across all six guards; verified byte-identical before the move (todo 380).
FRESHNESS_SECONDS = 120
OUTBOUND_MARKER_GLOB = ".outbound-marker*"

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


def strip_quotes(tok: str) -> str:
    if len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in ("\"", "'"):
        return tok[1:-1]
    return tok


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
