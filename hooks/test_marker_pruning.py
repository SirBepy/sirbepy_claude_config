"""Self-test for _marker_pruning.py (todo 917).

Run directly: python hooks/test_marker_pruning.py
"""

import os
import sys
import tempfile
import time
from pathlib import Path

import _testlib

pruning = _testlib.load_module(
    "pruning", Path(__file__).resolve().parent / "_marker_pruning.py"
)

FRESHNESS_SECONDS = 120


def _age(path: Path, seconds_old: float) -> None:
    """Backdate a file's mtime by `seconds_old`, POSIX-safe."""
    now = time.time()
    then = now - seconds_old
    os.utime(path, (then, then))


fails = []

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)

    expired = tmpdir / ".commit-marker-expired"
    expired.touch()
    _age(expired, FRESHNESS_SECONDS + 30)

    fresh = tmpdir / ".commit-marker-fresh"
    fresh.touch()
    _age(fresh, 5)

    near_boundary = tmpdir / ".commit-marker-near-boundary"
    near_boundary.touch()
    _age(near_boundary, FRESHNESS_SECONDS - 10)  # inside the freshness window, kept

    legacy_session = tmpdir / ".commit-marker-session-abc123"
    legacy_session.touch()
    _age(legacy_session, FRESHNESS_SECONDS + 999)  # old, but excluded by prefix

    pruned_count = pruning.prune_expired_markers(
        tmpdir, ".commit-marker*", FRESHNESS_SECONDS,
        exclude_prefix=".commit-marker-session-",
    )

    if not _testlib.report(pruned_count == 1, f"exactly one marker pruned (got {pruned_count})"):
        fails.append("pruned_count")
    if not _testlib.report(not expired.exists(), "expired marker is gone"):
        fails.append("expired gone")
    if not _testlib.report(fresh.exists(), "fresh marker survives"):
        fails.append("fresh survives")
    if not _testlib.report(near_boundary.exists(), "marker still inside the freshness window survives"):
        fails.append("near boundary survives")
    if not _testlib.report(legacy_session.exists(), "excluded legacy-session-prefixed marker survives despite its age"):
        fails.append("legacy session survives")

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    label = "empty directory prunes nothing, no crash"
    got = pruning.prune_expired_markers(tmpdir, ".commit-marker*", FRESHNESS_SECONDS)
    if not _testlib.report(got == 0, f"{label} (got {got})"):
        fails.append(label)

label = "a directory that does not exist on disk prunes nothing, no crash"
missing_dir = Path(tempfile.gettempdir()) / "does-not-exist-marker-pruning-test"
got = pruning.prune_expired_markers(missing_dir, ".commit-marker*", FRESHNESS_SECONDS)
if not _testlib.report(got == 0, f"{label} (got {got})"):
    fails.append(label)

sys.exit(_testlib.summarize(fails, style="count"))
