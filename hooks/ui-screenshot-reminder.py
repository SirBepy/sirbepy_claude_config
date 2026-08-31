"""Stop hook (todo 326): remind Claude to show Joe a screenshot after a turn
that touched UI-ish files. Global, per CLAUDE.md's "UI & visual changes"
section - Joe wants this applied everywhere, not copied per-repo (2026-08-16,
supersedes todo 326's original zng-app/zng-biller scope).

Todo 821 (2026-08-31): the original design fired at most once per session
(a marker file suppressed every later call, session-wide, forever). Replaced
with a stateless compare: fire whenever the newest UI-ish changed file is
newer than the newest screenshot under .for_bepy/screenshots/, so a
screenshot taken then followed by further unshot UI edits fires again
instead of staying quiet for the rest of the session.

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

GIT_TIMEOUT_SECONDS = 10
SCREENSHOTS_DIRNAME = Path(".for_bepy") / "screenshots"

UI_EXTENSIONS = {".tsx", ".jsx", ".vue", ".svelte", ".css", ".scss", ".dart"}
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


def newest_mtime(paths: list[Path]) -> float | None:
    """Newest mtime among `paths`, skipping any that no longer exist
    (deleted/renamed since the git listing was taken). None if all missing.
    """
    newest: float | None = None
    for p in paths:
        try:
            mtime = p.stat().st_mtime
        except OSError:
            continue
        if newest is None or mtime > newest:
            newest = mtime
    return newest


def newest_screenshot_mtime(cwd: str) -> float | None:
    """Newest .png mtime anywhere under `cwd`/.for_bepy/screenshots/, across
    every session subfolder - the hook has no reliable way to resolve its
    own session's screenshot-folder id, so it scans the whole tree rather
    than guessing one folder.
    """
    base = Path(cwd or ".") / SCREENSHOTS_DIRNAME
    if not base.is_dir():
        return None
    try:
        return newest_mtime(list(base.rglob("*.png")))
    except OSError:
        return None


def main() -> None:
    payload = read_payload()

    session_id = payload.get("session_id") or ""
    if not session_id:
        sys.exit(0)

    cwd = payload.get("cwd") or "."
    files = changed_files(cwd)
    ui_files = [Path(cwd) / f for f in files if is_ui_path(f)]
    ui_mtime = newest_mtime(ui_files)
    if ui_mtime is None:
        sys.exit(0)

    screenshot_mtime = newest_screenshot_mtime(cwd)
    if screenshot_mtime is not None and screenshot_mtime >= ui_mtime:
        sys.exit(0)

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
