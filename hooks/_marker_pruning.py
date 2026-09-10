"""Age-based pruning for legacy per-commit markers (todo 917).

Scope: `hooks/.commit-marker-<suffix>` only - one-shot markers a
`/mega-todos` builder writes for a single commit, consumed (deleted) by
`_hooklib.consume_fresh_marker`/`oldest_fresh_marker`, both of which only
ever consider a marker within FRESHNESS_SECONDS of its own mtime. Once a
marker ages past that window it is *already* permanently unreachable to the
guard's own consumption logic - nothing will ever pick it up again, whether
its commit landed some other way or never happened at all. Deleting it here
therefore changes no session's ability to commit; it only reclaims space a
marker was occupying after it had already gone inert.

Session markers (`hooks/.session-markers/<session_id>`) are NOT in scope
here - they are checked by `.exists()` for the life of a session, with no
freshness window, so age alone can never prove one is safe to delete (a
long-running session must not lose its marker just for being slow). Their
pruning is liveness-based and lives in `write-session-marker.ps1` instead,
keyed off `~/.claude/sessions/*.json` (the same pid registry
`skills/close/rename-session.ps1 -Close` already trusts, per todo 60: a raw
process-tree walk is not trustworthy here, only a sessionId->pid lookup is).
`exclude_prefix` below exists so a caller can protect the legacy session-
marker prefix (`.commit-marker-session-`), which shares this directory and
this glob but is a persistent marker, not a disposable one.
"""

import time
from pathlib import Path


def prune_expired_markers(
    marker_dir: Path,
    glob_pattern: str,
    freshness_seconds: int,
    exclude_prefix: str | None = None,
) -> int:
    """Delete every marker in `marker_dir` matching `glob_pattern` whose
    mtime is older than `freshness_seconds`. Returns the count removed.

    A per-file OSError (stat or unlink) is swallowed and that file is
    skipped: a concurrent guard invocation may have already consumed or
    pruned it first, and losing that race is not an error, exactly the
    convention `_hooklib.consume_fresh_marker` already uses for its own
    unlink.
    """
    if not marker_dir.exists():
        return 0
    now = time.time()
    pruned = 0
    for path in marker_dir.glob(glob_pattern):
        if exclude_prefix and path.name.startswith(exclude_prefix):
            continue
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if now - mtime <= freshness_seconds:
            continue
        try:
            path.unlink()
            pruned += 1
        except OSError:
            pass
    return pruned
