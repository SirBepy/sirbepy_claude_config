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

Todo 487 (2026-09-01): "changed files" used to mean the whole working tree's
`git diff`/untracked set, so any pre-existing dirty UI file (a peer session's
edit, or leftover dirt from an earlier turn) fired the reminder on a turn
that never touched it, including read-only turns. Attribution now comes from
the transcript's own tool_use blocks since the last real user message (the
same boundary em-dash-guard.py uses), so only files THIS turn's own
Edit/Write/MultiEdit/NotebookEdit calls touched can trigger it. The repo used
for the screenshot-freshness scan is resolved from the edited file's own git
root, not payload["cwd"] (which follows the last Bash cwd and can drift to a
different repo than the one actually edited).

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


EDIT_TOOL_SUFFIXES = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def is_tool_result_entry(entry: dict) -> bool:
    """A tool_result is wrapped in a `type: user` entry in this transcript
    format, distinguishable from a real human prompt only by content shape:
    its `message.content` is a list of blocks carrying `type: tool_result`
    (mirrors em-dash-guard.py's identical helper, todo 506)."""
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


def turn_edited_paths(transcript_path: str) -> list[str]:
    """File paths this turn's own Edit/Write/MultiEdit/NotebookEdit tool
    calls touched, read from the transcript instead of `git status` - the
    todo 487 fix: tree-wide dirt (a peer session's file, or a leftover dirty
    file from an earlier turn) can no longer be attributed to this turn.
    """
    if not transcript_path:
        return []
    paths: list[str] = []
    for name, tool_input in iter_turn_tool_uses(transcript_path):
        suffix = name.rsplit("__", 1)[-1] if "__" in name else name
        if suffix not in EDIT_TOOL_SUFFIXES:
            continue
        p = tool_input.get("file_path") or tool_input.get("notebook_path")
        if isinstance(p, str) and p:
            paths.append(p)
    return paths


def resolve_repo_root(path: Path) -> str | None:
    """Git repo root containing `path`, so the screenshot-freshness scan
    stays pinned to the repo the turn actually edited rather than
    payload["cwd"] (which follows the last Bash cwd and can drift, todo 487).
    None if `path` isn't inside a git repo or git fails.
    """
    proc = _run_git(str(path.parent), ["rev-parse", "--show-toplevel"])
    if proc is None or proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


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

    transcript_path = payload.get("transcript_path") or ""
    edited = turn_edited_paths(transcript_path)
    ui_files = [Path(p) for p in edited if is_ui_path(p)]
    ui_mtime = newest_mtime(ui_files)
    if ui_mtime is None:
        sys.exit(0)

    repo_root = resolve_repo_root(ui_files[0]) or payload.get("cwd") or "."
    screenshot_mtime = newest_screenshot_mtime(repo_root)
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
