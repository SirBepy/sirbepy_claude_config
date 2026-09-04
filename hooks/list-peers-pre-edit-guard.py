"""PreToolUse guard on Edit/Write (todo 458): warns, at most once per session
per repo, if another Conductor session shares this repo before the first edit.
The commit-time half of the `list_peers` rule already has teeth (`/commit`
step 7a); this is the pre-edit half, previously just a prose clause the model
could forget mid-task.

Reachability: the daemon's hooks_server already answers `list_peers` over
HTTP (`POST http://127.0.0.1:27182/channel/list-peers`, body
`{"session_id": ...}`), the same port every other global hook here already
curls (see settings.json's SessionStart/SessionEnd/Stop entries). The
`session_id` Claude Code's own hook payload carries is the exact id the
daemon spawned `claude --session-id <id>` with (claude_usage_in_taskbar's
`daemon/lifecycle/spawn.rs`), so it resolves to the same registry entry a
live `list_peers` MCP call would see - no separate discovery step needed.

Fails open on every non-"peers found" outcome (unreachable daemon, unknown
session, non-git cwd) and marks the session+repo pair so later edits in the
same turn/session never re-query - `main()`'s early-exit chain is the
single place all four skip conditions funnel through.

Second sensor (todo 895): `list_peers` returned empty twice while another
session committed underneath it. The marker now also carries this session's
last-seen `HEAD` sha; a later edit whose live `HEAD` differs warns on that
alone, even with zero peers reported, since a wrong daemon answer never
changes what git itself recorded.
"""

import hashlib
import json
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import GIT_TIMEOUT_SECONDS, git_repo_root, read_payload, allow_with_warning
except Exception as e:
    sys.stderr.write(f"[list-peers-pre-edit-guard] FATAL: cannot import _hooklib ({e}); failing open.\n")
    sys.exit(0)

DAEMON_PORT = 27182
REQUEST_TIMEOUT_SECONDS = 1.5
# OS temp dir, not the repo: this is machine-local runtime state, never
# something to gitignore or commit (mirrors the ban on reusing another
# guard's hooks/.session-markers/).
MARKER_DIR = Path(tempfile.gettempdir()) / "claude-list-peers-guard"

# Kept as a module-level name (not just the bare import) so this guard's
# own test suite can call `guard.repo_root(...)` unmodified (todo 874).
repo_root = git_repo_root


def marker_path(session_id: str, repo: str) -> Path:
    digest = hashlib.sha1(repo.encode("utf-8")).hexdigest()[:16]
    return MARKER_DIR / f"{session_id}__{digest}"


def get_head(repo: str) -> str | None:
    """Current `HEAD` sha, or None (no commits yet, or a git failure)."""
    try:
        proc = subprocess.run(
            ["git", "-C", repo, "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def write_marker(marker: Path, head: str | None) -> None:
    try:
        MARKER_DIR.mkdir(parents=True, exist_ok=True)
        marker.write_text(head or "", encoding="utf-8")
    except OSError:
        pass  # best-effort; a missed marker just means one more check later


def fetch_peers(session_id: str, port: int) -> list | None:
    """Live peers sharing this session's project, or None on ANY failure
    (daemon down, session not registered, malformed response) - the caller
    treats every failure identically to "zero peers", never distinguishing.
    """
    body = json.dumps({"session_id": session_id}).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/channel/list-peers",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError):
        return None
    if data.get("ok") is False:
        return None
    peers = data.get("peers")
    return peers if isinstance(peers, list) else None


def peer_label(peer: dict) -> str:
    name = peer.get("name") or peer.get("session_id") or "unknown"
    branch = peer.get("branch")
    return f"{name} ({branch})" if branch else str(name)


def main() -> None:
    payload = read_payload()
    session_id = payload.get("session_id") or ""
    cwd = payload.get("cwd") or ""
    if not session_id or not cwd:
        sys.exit(0)

    repo = repo_root(cwd)
    if not repo:
        sys.exit(0)

    marker = marker_path(session_id, repo)
    current_head = get_head(repo)
    # NotebookEdit sends notebook_path, not file_path; same fallback the two sibling
    # guards on this matcher use (sensitive-file-guard.py:58, secret-write-guard.py:130).
    tool_input = payload.get("tool_input") or {}
    file_path = tool_input.get("file_path") or tool_input.get("notebook_path") or "this file"

    if marker.exists():
        recorded = marker.read_text(encoding="utf-8").strip()
        current = current_head or ""
        if current == recorded:
            sys.exit(0)
        # HEAD moved since this session's own last check (including "went from no
        # commits to one"): proof of a peer even though list_peers reported none.
        write_marker(marker, current_head)
        allow_with_warning(
            f"[list-peers-pre-edit-guard] HEAD moved ({recorded[:8] or 'none'} -> "
            f"{current[:8] or 'none'}) in this repo without this session committing, "
            f"while editing {file_path}. list_peers may be wrong - announce on the "
            "repo channel, narrow this edit's pathspec, or stop and investigate."
        )

    peers = fetch_peers(session_id, DAEMON_PORT)
    write_marker(marker, current_head)

    if not peers:
        sys.exit(0)

    names = ", ".join(peer_label(p) for p in peers)
    allow_with_warning(
        f"[list-peers-pre-edit-guard] {len(peers)} peer session(s) share this repo "
        f"({names}) while editing {file_path}. Call list_peers/post_message before "
        f"proceeding if your edit might collide."
    )


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[list-peers-pre-edit-guard] hook error, failing open: {e}\n")
        sys.exit(0)
