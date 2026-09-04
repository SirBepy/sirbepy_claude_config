"""Shared-checkout peer logic (todo 911 split, from todo 797/775): live-peer
probing and stash-sweep file listing that gate the SHARED tier.

match_shared_checkout_hit() itself stays defined in destructive-command-
guard.py rather than moving here: hooks/test_destructive_command_guard.py
monkeypatches is_main_checkout/fetch_peer_count as attributes of the loaded
entry-point module and then calls match_shared_checkout_hit() through that
same module object. A function's bare-name lookups resolve against its OWN
module's globals, so if match_shared_checkout_hit lived here, the entry
file's monkeypatch would silently miss it and the test would exercise the
real git/network calls instead of the mocks.
"""

import json
import re
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

from _destructive_guard_shared import GIT_STASH_ANCHOR_RE, GIT_STASH_SAFE_SUBCMD_RE, verb_segments


def is_main_checkout(cwd: str) -> bool:
    """True only for a repo's primary worktree. A linked worktree's --git-dir
    sits under <common-dir>/worktrees/<name>, so it never equals --git-common-
    dir the way the main checkout's does; any git failure returns False.
    """
    try:
        common = subprocess.run(["git", "-C", cwd, "rev-parse", "--git-common-dir"],
                                 capture_output=True, text=True, timeout=10)
        gitdir = subprocess.run(["git", "-C", cwd, "rev-parse", "--git-dir"],
                                 capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return False
    if common.returncode != 0 or gitdir.returncode != 0:
        return False
    base = Path(cwd)
    try:
        return (base / common.stdout.strip()).resolve() == (base / gitdir.stdout.strip()).resolve()
    except OSError:
        return False


def fetch_peer_count(session_id: str) -> int:
    """Live peers sharing this session's project, via the same Conductor
    daemon endpoint list-peers-pre-edit-guard.py already proved reachable
    (todo 458). Any failure reports 0, matching this file's fail-open
    convention - a false negative here costs one warning, never a block.
    """
    if not session_id:
        return 0
    body = json.dumps({"session_id": session_id}).encode("utf-8")
    req = urllib.request.Request(
        "http://127.0.0.1:27182/channel/list-peers",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError):
        return 0
    if data.get("ok") is False:
        return 0
    peers = data.get("peers")
    return len(peers) if isinstance(peers, list) else 0


def stash_pathspec_args(seg: str) -> list:
    """Positional args after `git stash [push|save]`, following a literal
    `--` if present. No `--` means "whole tree" (bare stash, or push/save
    with no pathspec restriction) - the conservative reading for a sweep.
    """
    rest = GIT_STASH_ANCHOR_RE.sub("", seg, count=1)
    rest = re.sub(r"^\s*(push|save)\b", "", rest, flags=re.IGNORECASE)
    if "--" not in rest:
        return []
    return [t for t in rest.split("--", 1)[1].split() if t]


def stash_swept_files(command: str, cwd: str) -> list:
    """`git status` scoped to the stash's own pathspec (whole tree if none),
    so the prompt names what a peer's uncommitted edits would look like at
    risk - best-effort, empty on any git failure (todo 775).
    """
    pathspecs = []
    for seg in verb_segments(command):
        if GIT_STASH_SAFE_SUBCMD_RE.match(seg):
            continue
        if GIT_STASH_ANCHOR_RE.match(seg):
            pathspecs = stash_pathspec_args(seg)
            break
    cmd = ["git", "-C", cwd, "status", "--porcelain", "--no-renames"]
    if pathspecs:
        cmd += ["--"] + pathspecs
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    return [line[3:].strip() for line in proc.stdout.splitlines() if len(line) > 3]
