"""Self-test for write-session-marker.ps1's opportunistic pruning (todo 917).

Run directly: python hooks/test_write_session_marker.py

Drives the real script via powershell.exe against fixture directories only
(-SessionMarkerDir / -SessionsRegistryDir overrides) - never the real
hooks/.session-markers/ or ~/.claude/sessions/. Proves the liveness rule in
both directions: a marker whose session has no live record (or a dead pid)
is pruned; a marker whose session resolves to a currently-running process is
kept.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

SCRIPT = Path(__file__).resolve().parent / "write-session-marker.ps1"
TIMEOUT_SECONDS = 30

fails = []


def run_script(session_id: str, marker_dir: Path, registry_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            "powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
            "-SessionId", session_id,
            "-SessionMarkerDir", str(marker_dir),
            "-SessionsRegistryDir", str(registry_dir),
        ],
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
    )


def write_registry_record(registry_dir: Path, name: str, session_id: str, pid: int) -> None:
    registry_dir.mkdir(parents=True, exist_ok=True)
    (registry_dir / f"{name}.json").write_text(
        json.dumps({"sessionId": session_id, "pid": pid}), encoding="utf-8"
    )


def exited_pid() -> int:
    """A pid that genuinely ran and has since exited - unlike a hardcoded
    guess (PID 0 is Windows' real, always-alive Idle process, proven live
    via `Get-Process -Id 0` while writing this test), this is provably dead
    by construction: spawned, waited on, so it can't still be running.
    """
    proc = subprocess.Popen(["cmd", "/c", "exit", "0"])
    pid = proc.pid
    proc.wait(timeout=10)
    return pid


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    marker_dir = tmpdir / ".session-markers"
    registry_dir = tmpdir / "sessions"
    marker_dir.mkdir()

    own_session_id = "own-session-under-test"

    # --- Direction 1: a marker whose session is provably GONE gets pruned ---

    # 1a. No registry record at all for this session id.
    dead_no_record = marker_dir / "dead-no-record"
    dead_no_record.touch()

    # 1b. A registry record exists but points at a pid that is not running.
    dead_stale_pid = marker_dir / "dead-stale-pid"
    dead_stale_pid.touch()
    write_registry_record(registry_dir, "stale", "dead-stale-pid", exited_pid())

    # --- Direction 2: a marker whose session IS live must survive ---

    # 2. A registry record pointing at THIS test process's own pid - alive
    # by construction, since it's the process running this very test.
    live_session_id = "live-session-under-test"
    live_marker = marker_dir / live_session_id
    live_marker.touch()
    write_registry_record(registry_dir, "live", live_session_id, os.getpid())

    proc = run_script(own_session_id, marker_dir, registry_dir)
    if not _testlib.report(proc.returncode == 0, f"script exits 0 (stderr: {proc.stderr!r})"):
        fails.append("exit code")

    own_marker = marker_dir / own_session_id
    if not _testlib.report(own_marker.exists(), "the script's own new marker was written"):
        fails.append("own marker written")

    if not _testlib.report(not dead_no_record.exists(), "marker with no registry record at all is pruned"):
        fails.append("no-record pruned")
    if not _testlib.report(not dead_stale_pid.exists(), "marker whose registry record points at a dead pid is pruned"):
        fails.append("stale-pid pruned")
    if not _testlib.report(live_marker.exists(), "marker whose registry record points at a live pid survives"):
        fails.append("live survives")

# --- Malformed registry entries are skipped, not treated as proof of death ---

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    marker_dir = tmpdir / ".session-markers"
    registry_dir = tmpdir / "sessions"
    marker_dir.mkdir()
    registry_dir.mkdir()

    orphan_id = "session-with-unparsable-record"
    orphan_marker = marker_dir / orphan_id
    orphan_marker.touch()
    (registry_dir / "broken.json").write_text("{not valid json", encoding="utf-8")

    proc = run_script("writer-session", marker_dir, registry_dir)
    label = "a marker whose only matching record is unparsable is pruned (absence of proof is not proof of life)"
    if not _testlib.report(proc.returncode == 0 and not orphan_marker.exists(), label):
        fails.append(label)

# --- The writing session's own marker is never pruned by its own write ---

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    marker_dir = tmpdir / ".session-markers"
    registry_dir = tmpdir / "sessions"
    marker_dir.mkdir()

    sid = "self-write-session"
    proc = run_script(sid, marker_dir, registry_dir)
    marker = marker_dir / sid
    label = "a session's own freshly-written marker survives even with no registry record for itself"
    if not _testlib.report(proc.returncode == 0 and marker.exists(), label):
        fails.append(label)

sys.exit(_testlib.summarize(fails, style="count"))
