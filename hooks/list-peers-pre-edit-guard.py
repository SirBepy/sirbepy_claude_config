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
same turn/session never re-query - `handle_pre_edit()`'s early-exit chain is
the single place all four skip conditions funnel through.

Second sensor (todo 895): `list_peers` returned empty twice while another
session committed underneath it. The marker now also carries this session's
last-seen `HEAD` sha; a later edit whose live `HEAD` differs warns on that
alone, even with zero peers reported, since a wrong daemon answer never
changes what git itself recorded.

Own-commit refresh (todo 907): the sensor above cannot tell "a peer committed"
apart from "I just committed" by sha alone - both move HEAD, so the fix for
todo 895 also warned on the session's own ordinary commits. A second
PostToolUse arm, wired in settings.json on Bash|PowerShell, watches for this
session's own `git commit` and re-syncs the marker to the resulting HEAD the
moment it lands, so the very next edit's pre-check compares against a marker
that already accounts for this session's own history. A failed/rejected
commit never moves HEAD, so refreshing unconditionally on any `git commit`
invocation is always safe - it just re-reads whatever HEAD already is. This
cannot distinguish a peer commit that lands in the narrow window between this
session's own edits and its own `git commit` call (no Edit/Write fires in
that window to catch it) - accepted, see todo 907's own Approach; the
PreToolUse sensor above still catches any peer commit that lands between two
of this session's edits, which is the case todo 895 was filed for.
"""

import hashlib
import json
import shlex
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

# Global flags that take a separate following token as their value, so that
# token is never mistaken for the `commit` subcommand itself. Same shape as
# commit-guard.py's own VALUE_FLAGS, kept as an independent copy since the
# two guards ask a different question: commit-guard decides whether to BLOCK
# the call, this one decides whether to REFRESH a marker after it already ran.
_GIT_VALUE_FLAGS = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def is_git_commit_command(command: str) -> bool:
    """True if `command` contains a real `git commit` subcommand call,
    walking past global flags (and their values) token by token so
    `commit-graph`, `--grep="commit"`, or a message/path containing "commit"
    never false-positives a marker refresh."""
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        return False
    for i, tok in enumerate(tokens):
        if tok != "git":
            continue
        j = i + 1
        while j < len(tokens) and tokens[j].startswith("-"):
            if tokens[j] in _GIT_VALUE_FLAGS and "=" not in tokens[j]:
                j += 2
            else:
                j += 1
        if j < len(tokens) and tokens[j] == "commit":
            return True
    return False


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


def handle_post_tool_use(payload: dict) -> None:
    """Own-commit refresh (todo 907): after this session's own `git commit`
    lands, re-sync the marker to the resulting HEAD before any later edit's
    pre-check can compare against a stale, pre-commit value."""
    if payload.get("tool_name") not in ("Bash", "PowerShell"):
        sys.exit(0)
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    if not is_git_commit_command(command):
        sys.exit(0)
    session_id = payload.get("session_id") or ""
    cwd = payload.get("cwd") or ""
    if not session_id or not cwd:
        sys.exit(0)
    repo = repo_root(cwd)
    if not repo:
        sys.exit(0)
    write_marker(marker_path(session_id, repo), get_head(repo))
    sys.exit(0)


def handle_pre_edit(payload: dict) -> None:
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


def main() -> None:
    payload = read_payload()
    if payload.get("hook_event_name") == "PostToolUse":
        handle_post_tool_use(payload)
        return
    handle_pre_edit(payload)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[list-peers-pre-edit-guard] hook error, failing open: {e}\n")
        sys.exit(0)
