#!/usr/bin/env python3
"""Local statusLine for Claude Code (todo 432): no network, no npx.
Fields come straight from the stdin JSON per code.claude.com/docs/en/statusline
(context_window.remaining_percentage is precomputed by Claude Code itself, so
this does not duplicate context-left.mjs's own compute-from-transcript logic).
Git branch is the one thing not in the payload; cached per session_id with a
600s TTL (docs' own recommended cache key, TTL borrowed from the harvested Go
statusline) since `git branch` runs on every render otherwise.
"""

import json
import os
import subprocess
import sys
import tempfile
import time

CACHE_TTL = 600


def read_input():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def git_branch(cwd, session_id):
    if not cwd:
        return None
    cache = os.path.join(tempfile.gettempdir(), f"claude-statusline-git-{session_id or 'nosession'}")
    try:
        if os.path.exists(cache) and time.time() - os.path.getmtime(cache) < CACHE_TTL:
            with open(cache, "r", encoding="utf-8") as f:
                return f.read().strip() or None
    except Exception:
        pass
    branch = None
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "branch", "--show-current"],
            capture_output=True, text=True, timeout=1,
        )
        branch = out.stdout.strip() or None
    except Exception:
        branch = None
    try:
        with open(cache, "w", encoding="utf-8") as f:
            f.write(branch or "")
    except Exception:
        pass
    return branch


def main():
    data = read_input()
    parts = []

    model = (data.get("model") or {}).get("display_name")
    if model:
        parts.append(model)

    style = (data.get("output_style") or {}).get("name")
    if style:
        parts.append(style)

    remaining = (data.get("context_window") or {}).get("remaining_percentage")
    if isinstance(remaining, (int, float)):
        parts.append(f"ctx {round(remaining)}%")

    duration_ms = (data.get("cost") or {}).get("total_duration_ms")
    if isinstance(duration_ms, (int, float)):
        parts.append(f"{int(duration_ms // 60000)}m")

    cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd")
    branch = git_branch(cwd, data.get("session_id"))
    if branch:
        parts.append(branch)

    print(" | ".join(parts) if parts else "claude")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("claude")
