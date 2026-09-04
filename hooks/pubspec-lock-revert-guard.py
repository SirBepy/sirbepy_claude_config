"""Two hook events, one module (todo 832): revert pubspec.lock when a
`flutter analyze`/`flutter run` invocation is the ONLY thing that dirtied
it. Both commands run an implicit `pub get` that rewrites the lock with
transitive-dependency bumps unrelated to any real change; zng-app's own
commit-style.md says to leave that churn uncommitted, and this automates
the `git checkout -- pubspec.lock` a session was doing by hand 4+ times.

PreToolUse: snapshots `git status --porcelain` for the nearest pubspec.lock
dir to a temp marker, keyed by session id + dir. Never blocks - it only
records a baseline.

PostToolUse: diffs the post-command dirty set against that baseline. Only
reverts if the diff is exactly {"pubspec.lock"} - so a lock already dirty
before the command (in both sets, so absent from the diff) is left alone,
and a genuine pubspec.yaml dependency bump (present in the diff alongside
the lock) is left alone too. Marker missing or stale: no baseline, no
revert - conservative by construction, never by a second check bolted on.

Any git/marker failure fails open silently; a missed revert is a future
manual chore, never worth surfacing or blocking a Flutter session over.
"""

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload, GIT_TIMEOUT_SECONDS, FRESHNESS_SECONDS, is_command_position
except Exception as e:
    sys.stderr.write(f"[pubspec-lock-revert-guard] cannot import _hooklib ({e}); failing open.\n")
    sys.exit(0)

# The optional `fvm ` prefix keeps the match's own start (what
# is_command_position below checks) at the real invocation's start rather
# than at "flutter" - `fvm flutter analyze` is this guard's own typical case.
COMMAND_RE = re.compile(r"\b(?:fvm\s+)?flutter\s+(analyze|run)\b", re.IGNORECASE)
MARKER_DIR = Path(tempfile.gettempdir()) / "claude-pubspec-lock-guard"


def find_nearest_pubspec_dir(start_dir: Path) -> Path | None:
    d = start_dir
    for _ in range(64):
        if (d / "pubspec.lock").is_file():
            return d
        if d.parent == d:
            return None
        d = d.parent
    return None


def marker_path(session_id: str, pubspec_dir: Path) -> Path:
    digest = hashlib.sha1(f"{session_id}:{pubspec_dir}".encode("utf-8")).hexdigest()
    return MARKER_DIR / f"{digest}.json"


def git_status_paths(repo_dir: str) -> set[str] | None:
    try:
        proc = subprocess.run(
            ["git", "-C", repo_dir, "status", "--porcelain", "--no-renames"],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return {line[3:].strip() for line in proc.stdout.splitlines() if len(line) > 3}


def handle_pre(payload: dict, pubspec_dir: Path) -> None:
    dirty = git_status_paths(str(pubspec_dir))
    if dirty is None:
        return
    marker = marker_path(payload.get("session_id") or "", pubspec_dir)
    try:
        MARKER_DIR.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"dirty": sorted(dirty), "ts": time.time()}), encoding="utf-8")
    except OSError:
        pass


def handle_post(payload: dict, pubspec_dir: Path) -> None:
    marker = marker_path(payload.get("session_id") or "", pubspec_dir)
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    try:
        marker.unlink()
    except OSError:
        pass

    if time.time() - data.get("ts", 0) > FRESHNESS_SECONDS:
        return

    post_dirty = git_status_paths(str(pubspec_dir))
    if post_dirty is None:
        return

    newly_dirty = post_dirty - set(data.get("dirty") or [])
    if newly_dirty != {"pubspec.lock"}:
        return

    try:
        proc = subprocess.run(
            ["git", "-C", str(pubspec_dir), "checkout", "--", "pubspec.lock"],
            capture_output=True, text=True, timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return
    if proc.returncode == 0:
        print(f"[pubspec-lock-revert-guard] Reverted pubspec.lock pub-get churn in {pubspec_dir}.")


def main() -> None:
    payload = read_payload()
    if payload.get("tool_name") not in ("Bash", "PowerShell"):
        sys.exit(0)
    command = (payload.get("tool_input") or {}).get("command", "") or ""
    # todo 908: anchored to command position - a commit message or note
    # merely quoting "flutter analyze" must not snapshot/revert the lock.
    if not any(is_command_position(command, m.start()) for m in COMMAND_RE.finditer(command)):
        sys.exit(0)

    pubspec_dir = find_nearest_pubspec_dir(Path(payload.get("cwd") or "."))
    if pubspec_dir is None:
        sys.exit(0)

    event = payload.get("hook_event_name")
    if event == "PreToolUse":
        handle_pre(payload, pubspec_dir)
    elif event == "PostToolUse":
        handle_post(payload, pubspec_dir)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[pubspec-lock-revert-guard] hook error, failing open: {e}\n")
        sys.exit(0)
