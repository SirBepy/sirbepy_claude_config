"""Self-test for reserve-todo-id.ps1's stale-reservation pruning (todo 988).

Run directly: python tools/test_close_reserve_todo_id.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Drives the real script via powershell.exe against scratch backlog
directories under tempfile.TemporaryDirectory() - never the real
.claude/todos/.

A bare pid is not a reliable liveness signal: Windows recycles pids, so a
dead session's marker can read as alive forever once some unrelated process
inherits the number. This proves the fix in both directions: a marker whose
recorded pid is alive but whose start time does NOT match (the recycled-pid
case) is pruned once past the 4h threshold, never before; a marker whose pid
AND start time both match a genuinely live process is never pruned, no
matter its age; and a pre-fix marker with no start-time field at all clears
via the 24h age-only fallback instead of staying immortal.
"""

import datetime
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))

import _testlib  # noqa: E402

SCRIPT = Path(os.environ.get(
    "CLOSE_RESERVE_SCRIPT", str(ROOT / "skills" / "close" / "reserve-todo-id.ps1")
))
TIMEOUT_SECONDS = 60

fails = []


def run_script(repo_root: Path, now: "datetime.datetime | None" = None) -> subprocess.CompletedProcess:
    args = ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
            "-RepoRoot", str(repo_root)]
    if now is not None:
        # Pins the script's staleness clock to the SAME instant the fixture
        # mtimes below were computed from, so a 4h/24h boundary case can't
        # flip just because this process got scheduled late under concurrent
        # CI load (todo 1082) - the real failure mode, not the compare itself.
        args += ["-Now", now.isoformat()]
    return subprocess.run(
        args, capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
    )


def get_start_ticks(pid: int) -> int:
    proc = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
         f"(Get-Process -Id {pid}).StartTime.Ticks"],
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
    )
    return int(proc.stdout.strip())


def write_marker(path: Path, *, pid: int, start_ticks, age_hours: float, sentinel: str, anchor: float) -> str:
    """Writes a fixture reservation marker and returns its exact content, so a
    caller can later tell "this path still holds MY fixture" apart from "this
    path exists because the script reserved a brand new id at the same number
    after pruning freed it" - a freed id IS immediately eligible for reuse by
    design, so bare Test-Path after a run is not a safe pruned/survived check.

    `anchor` (an epoch seconds snapshot, not live time.time()) is what the
    mtime is aged relative to. The script is later called with that exact
    instant passed as -Now, so the 4h/24h boundary math stays fixed to the
    fixture's own reference point no matter how long this process is
    scheduling-delayed before it actually runs the script (todo 1082).
    """
    lines = [f"session: {sentinel}", f"pid: {pid}"]
    if start_ticks is not None:
        lines.append(f"procStartTicks: {start_ticks}")
    lines.append("reserved: 2026-01-01T00:00:00")
    content = "\r\n".join(lines) + "\r\n"
    # newline="" on both write and read: Python's universal-newline translation
    # would otherwise rewrite the literal \r\n already in `content` into \r\r\n
    # on write (and collapse it differently on read back), making an untouched
    # file compare unequal to itself.
    path.write_text(content, encoding="utf-8", newline="")
    old = anchor - age_hours * 3600
    os.utime(path, (old, old))
    return content


def survived(path: Path, original_content: str) -> bool:
    if not path.exists():
        return False
    try:
        return path.read_text(encoding="utf-8", newline="") == original_content
    except OSError:
        return False


own_pid = os.getpid()
own_ticks = get_start_ticks(own_pid)

with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp)
    todos = repo / ".claude" / "todos"
    todos.mkdir(parents=True)

    # Single reference instant for every fixture's mtime AND the script's own
    # staleness clock (-Now below) - the boundary math is relative to this
    # anchor, never to whatever the wall clock happens to read when the
    # script actually gets scheduled (todo 1082).
    anchor_dt = datetime.datetime.now()
    anchor = anchor_dt.timestamp()

    # A: two-signal, pid alive, ticks MATCH, age 100h - never pruned regardless of age.
    marker_a = todos / "101-.reserved"
    content_a = write_marker(marker_a, pid=own_pid, start_ticks=own_ticks, age_hours=100, sentinel="fixture-a", anchor=anchor)

    # B: two-signal, pid alive but ticks MISMATCH (recycled pid), age 5h (past 4h) - pruned.
    marker_b = todos / "102-.reserved"
    content_b = write_marker(marker_b, pid=own_pid, start_ticks=1, age_hours=5, sentinel="fixture-b", anchor=anchor)

    # C: two-signal, pid alive, ticks mismatch, age 2h (under 4h) - not yet stale.
    marker_c = todos / "103-.reserved"
    content_c = write_marker(marker_c, pid=own_pid, start_ticks=1, age_hours=2, sentinel="fixture-c", anchor=anchor)

    # D: legacy marker (no procStartTicks field), age 1h - survives (< 24h fallback).
    marker_d = todos / "104-.reserved"
    content_d = write_marker(marker_d, pid=own_pid, start_ticks=None, age_hours=1, sentinel="fixture-d", anchor=anchor)

    # E: legacy marker (no procStartTicks field), age 25h - pruned (> 24h fallback).
    marker_e = todos / "105-.reserved"
    content_e = write_marker(marker_e, pid=own_pid, start_ticks=None, age_hours=25, sentinel="fixture-e", anchor=anchor)

    proc = run_script(repo, now=anchor_dt)
    if not _testlib.report(proc.returncode == 0, f"script exits 0 (stderr: {proc.stderr!r})"):
        fails.append("exit code")

    if not _testlib.report(survived(marker_a, content_a), "live pid + matching start-time survives at any age"):
        fails.append("A: live survives")
    if not _testlib.report(not survived(marker_b, content_b), "live pid but mismatched start-time (recycled) is pruned past 4h"):
        fails.append("B: recycled pruned")
    if not _testlib.report(survived(marker_c, content_c), "mismatched start-time under 4h old is not yet pruned"):
        fails.append("C: under-4h survives")
    if not _testlib.report(survived(marker_d, content_d), "legacy marker (no start-time field) under 24h survives"):
        fails.append("D: legacy under-24h survives")
    if not _testlib.report(not survived(marker_e, content_e), "legacy marker (no start-time field) over 24h is pruned"):
        fails.append("E: legacy over-24h pruned")


# --- Functional smoke: still reserves the expected next id ---

with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp)
    todos = repo / ".claude" / "todos"
    todos.mkdir(parents=True)
    (todos / "05-foo.md").write_text("# 05-foo\n", encoding="utf-8")

    proc = run_script(repo)
    reserved = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    ok = proc.returncode == 0 and reserved == "6" and (todos / "6-.reserved").exists()
    if not _testlib.report(ok, f"reserves next id 6 after an existing 05-foo.md (out={proc.stdout!r})"):
        fails.append("functional next-id")

sys.exit(_testlib.summarize(fails, style="count"))
