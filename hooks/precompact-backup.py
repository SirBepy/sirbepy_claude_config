"""PreCompact hook (todo 426, scoped): cheap insurance against compaction
context loss. Fires right before manual or automatic compaction discards
context - the same class of loss as "task output files cleared on
completion" (see memory reference_task_output_files_cleared_on_completion),
which has no mitigation today. This hook gives a later session a breadcrumb
of what the compacting session was doing, without persisting anything a
compaction would not otherwise already keep safe on disk.

Deliberately excluded, and why:
  - The transcript file itself. Compaction summarizes what is IN Claude's
    context window; it does not delete or rewrite the on-disk transcript
    .jsonl. Copying the transcript here would duplicate data that already
    survives compaction untouched, for no insurance gain, while adding real
    cost (transcripts run to megabytes) and real risk (a transcript can
    contain anything the user pasted, including credentials).
  - Every form of free text: user prompts, assistant text, custom_instructions
    content, tool_result/tool output. All of it can carry pasted secrets or
    large blobs, and none of it is needed to answer "what was I doing" - file
    paths already answer that. Only structural fields are captured: ids, a
    trigger label, a timestamp, and the file PATHS (never content) recently
    touched by Edit/Write/MultiEdit/NotebookEdit/Read tool calls anywhere in
    this session's transcript.
  - Nothing outside this hook's own file. This is the file that gets edited
    to enable/expand capture later; do not build the "everything" version in
    the same pass that is proving the event even fires.

Write location: hooks/.session-markers/precompact-<session_id>.json. That
directory is the existing convention for per-session ephemeral hook state
(see send-message-stop-guard.py's silent-turns-<id> counters) and is already
git-ignored (.gitignore: "hooks/.session-markers/"), so this can never
pollute `git status` for any concurrent session sharing this checkout.

Growth bound: one file per session id, OVERWRITTEN on every compaction in
that session (never appended), so a single long session with many
compactions still occupies exactly one file. Cross-session accumulation is
bounded by self-pruning: every invocation first deletes any precompact-*
backup older than RETENTION_SECONDS via the shared _marker_pruning helper,
so the directory can only ever hold backups from sessions that compacted
within the retention window.

Never blocks: every exit path in main() is 0, and the outer try/except
around main() at the bottom exists specifically so an internal bug in this
hook (a bad payload shape, a permissions error writing the marker file, an
unexpected exception) fails open instead of ever surfacing as a blocked
compaction - the harness has no way to compact around a hook that hangs or
denies here, so this hook must never be the thing that breaks compaction.
"""

import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

try:
    from _hooklib import read_payload
    from _marker_pruning import prune_expired_markers
except Exception as e:
    sys.stderr.write(f"[precompact-backup] FATAL: cannot import shared libs ({e}); failing open.\n")
    sys.exit(0)

SESSION_MARKER_DIR = _HOOKS_DIR / ".session-markers"
MARKER_PREFIX = "precompact-"
MARKER_GLOB = f"{MARKER_PREFIX}*"
# 7 days: long enough that a session resumed the next day (or over a
# weekend) still finds its own last backup, short enough that a one-off
# session from weeks ago does not sit in this directory forever.
RETENTION_SECONDS = 7 * 24 * 60 * 60

_SAFE_SESSION_ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")

# Only these tool names' file-path arguments are captured - paths, never
# the content read/written. Read is included: "what was being read" is as
# useful a breadcrumb as "what was being edited".
FILE_PATH_TOOL_NAMES = {"Edit", "Write", "MultiEdit", "NotebookEdit", "Read"}
MAX_TOUCHED_FILES = 50


def _safe_session_id(session_id: str) -> bool:
    return bool(session_id) and bool(_SAFE_SESSION_ID_RE.match(session_id))


def _tool_suffix(name: str) -> str:
    return name.rsplit("__", 1)[-1] if "__" in name else name


def recently_touched_files(transcript_path: str, limit: int = MAX_TOUCHED_FILES) -> list[str]:
    """File PATHS (never content) touched by FILE_PATH_TOOL_NAMES tool calls
    anywhere in the transcript, most-recently-touched last, deduplicated,
    capped to `limit`. Whole-session scope on purpose: unlike a single-turn
    reminder hook, a compaction backup needs to answer "what was this
    session working on" across many turns, not just the latest one.

    Any read/parse failure returns an empty list rather than raising - this
    is pure best-effort enrichment, never load-bearing for the hook exiting
    cleanly.
    """
    if not transcript_path:
        return []
    path = Path(transcript_path)
    if not path.exists():
        return []
    seen_order: list[str] = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("type") != "assistant":
                    continue
                content = (entry.get("message") or {}).get("content") or []
                for block in content:
                    if not isinstance(block, dict) or block.get("type") != "tool_use":
                        continue
                    if _tool_suffix(block.get("name") or "") not in FILE_PATH_TOOL_NAMES:
                        continue
                    tool_input = block.get("input") or {}
                    p = tool_input.get("file_path") or tool_input.get("notebook_path")
                    if isinstance(p, str) and p:
                        if p in seen_order:
                            seen_order.remove(p)
                        seen_order.append(p)
    except OSError:
        return []
    return seen_order[-limit:]


def transcript_line_count(transcript_path: str) -> int:
    """A rough, content-free size signal (how many transcript entries exist),
    not the transcript itself. Best-effort: 0 on any failure."""
    if not transcript_path:
        return 0
    path = Path(transcript_path)
    if not path.exists():
        return 0
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for line in f if line.strip())
    except OSError:
        return 0


def build_backup(payload: dict) -> dict:
    transcript_path = payload.get("transcript_path") or ""
    return {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "hook_event_name": payload.get("hook_event_name") or "PreCompact",
        "session_id": payload.get("session_id") or "",
        "cwd": payload.get("cwd") or "",
        "trigger": payload.get("trigger") or "",
        "transcript_message_count": transcript_line_count(transcript_path),
        "recently_touched_files": recently_touched_files(transcript_path),
    }


def main() -> None:
    payload = read_payload()

    # Self-prune first so a directory of many old sessions' backups never
    # grows unbounded regardless of how often (or rarely) compaction fires.
    try:
        prune_expired_markers(SESSION_MARKER_DIR, MARKER_GLOB, RETENTION_SECONDS)
    except OSError:
        pass  # pruning is best-effort; never let it block the backup itself

    session_id = payload.get("session_id") or ""
    if not _safe_session_id(session_id):
        sys.exit(0)  # no safe filename to write; nothing else to do

    backup = build_backup(payload)

    try:
        SESSION_MARKER_DIR.mkdir(parents=True, exist_ok=True)
        marker_path = SESSION_MARKER_DIR / f"{MARKER_PREFIX}{session_id}.json"
        marker_path.write_text(json.dumps(backup, indent=2), encoding="utf-8")
    except OSError:
        pass  # best-effort insurance; a failed write must never block compaction

    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        sys.stderr.write(f"[precompact-backup] hook error, failing open: {e}\n")
        sys.exit(0)
