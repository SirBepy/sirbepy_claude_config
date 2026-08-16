"""Stop hook (todo 326): remind Claude to show Joe a screenshot after a turn
that touched UI-ish files. Global, per CLAUDE.md's "UI & visual changes"
section - Joe wants this applied everywhere, not copied per-repo (2026-08-16,
supersedes todo 326's original zng-app/zng-biller scope).

Pattern lifted from zng-admin's (gitignored, per-repo) reference Stop hook:
sentinel-gated to once per session, matching UI-ish paths in the session's
changed files. Ported to Python here since every other global hook is.

Non-blocking by design: any internal error must exit 0 silently (see the
bottom try/except), same as em-dash-guard. A missed reminder is fine; a
wedged Stop event is not.
"""

import json
import subprocess
import sys
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload
except Exception as e:
    sys.stderr.write(f"[ui-screenshot-reminder] FATAL: cannot import _hooklib ({e}); failing open.\n")
    sys.exit(0)

MARKER_DIR = _HOOKS_DIR
SESSION_MARKER_PREFIX = ".ui-screenshot-reminder-session-"
GIT_TIMEOUT_SECONDS = 10

UI_EXTENSIONS = {".tsx", ".jsx", ".vue", ".svelte", ".css", ".scss"}
UI_DIR_SEGMENTS = {"ui", "components", "widgets", "screens", "pages"}

REMINDER_TEXT = (
    "[ui-screenshot-reminder] This turn touched UI-ish files. Per CLAUDE.md's "
    "\"UI & visual changes\" rule: bring the app up via /supervised-run, give "
    "Joe the URL, and capture a screenshot through an isolated Claude-launched "
    "browser via SendUserFile - never raw window automation against Joe's own "
    "windows. Save it under .for_bepy/screenshots/<id>/, where <id> is the "
    "output of ~/.claude/skills/close/rename-session.ps1 -GetId. Skip this "
    "only if the change is pure logic/backend/config with no visual surface."
)


def session_marker_path(session_id: str) -> Path:
    return MARKER_DIR / f"{SESSION_MARKER_PREFIX}{session_id}"


def is_ui_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if Path(normalized).suffix.lower() in UI_EXTENSIONS:
        return True
    return any(part.lower() in UI_DIR_SEGMENTS for part in normalized.split("/"))


def _run_git(cwd: str, args: list[str]) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            ["git", "-C", cwd, *args],
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def changed_files(cwd: str) -> list[str]:
    """Tracked-dirty + untracked paths for `cwd`. Returns [] for a missing
    git binary, a non-repo cwd, or any git failure - never raises.
    """
    cwd = cwd or "."
    inside = _run_git(cwd, ["rev-parse", "--is-inside-work-tree"])
    if inside is None or inside.returncode != 0:
        return []

    files: list[str] = []
    tracked = _run_git(cwd, ["diff", "--name-only", "HEAD"])
    if tracked is not None and tracked.returncode == 0:
        files.extend(line.strip() for line in tracked.stdout.splitlines() if line.strip())
    untracked = _run_git(cwd, ["ls-files", "--others", "--exclude-standard"])
    if untracked is not None and untracked.returncode == 0:
        files.extend(line.strip() for line in untracked.stdout.splitlines() if line.strip())
    return files


def main() -> None:
    payload = read_payload()

    session_id = payload.get("session_id") or ""
    if not session_id:
        sys.exit(0)

    marker = session_marker_path(session_id)
    if marker.exists():
        sys.exit(0)

    files = changed_files(payload.get("cwd") or ".")
    if not any(is_ui_path(f) for f in files):
        sys.exit(0)

    try:
        marker.write_text("", encoding="utf-8")
    except OSError:
        pass

    print(json.dumps({"decision": "block", "reason": REMINDER_TEXT}))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[ui-screenshot-reminder] hook error, failing open: {e}\n")
        sys.exit(0)
