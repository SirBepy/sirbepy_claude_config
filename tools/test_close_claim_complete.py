"""Self-test for claim-todo.ps1 / complete-todo.ps1's batch-id handling.

Run directly: python tools/test_close_claim_complete.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Drives the real scripts via powershell.exe against scratch backlog directories
under tempfile.TemporaryDirectory() - never the real .claude/todos/.

Covers two todos:

- 1024 (batch claim strips zero padding): the confirmed root cause is
  PowerShell's OWN parser, not this repo's code - an unquoted `-Id 08,20`
  is tokenized as an array of numeric literals before claim-todo.ps1 ever
  runs, so "08" arrives as "8" with no way for the script to recover the
  padding after the fact. That means the RED/GREEN split here is not
  "padding survives" vs "padding is lost" (the loss is real PowerShell
  behavior, reproduced on purpose in test_unquoted_batch_strips_padding),
  it is "does complete-todo.ps1 still find and release the resulting
  unpadded claim file", which is what was actually broken and is fixed by
  _shared.ps1's new CanonicalId. The quoted form (`-Id "08,20"`) is the
  one that preserves padding on write, proven in test_quoted_batch_*.

- 1015 (complete-todo.ps1 batch -Id gives a misleading error): a
  comma-bearing -Id must fail with the real cause up front, not fall
  through to a "no todo file matching" message.

- 1083 (stale-claim reclaim trusts a bare pid): a claim file recording a
  pid that is alive on this machine used to be treated as live forever,
  even when that pid had been recycled by an unrelated process. The claim
  now also records procStartTicks; reclaim requires the pid to be alive
  AND its start time to match. Test F proves a mismatching start time
  (recycled-pid shape) reclaims once past the 4h mtime threshold; test G
  proves a genuinely live claim (matching start time) is never reclaimed;
  test H proves a legacy claim with no procStartTicks field keeps the old
  pid-only behavior.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))

import _testlib  # noqa: E402

# Override hooks exist solely so this same suite can be pointed at a baseline
# checkout to demonstrate RED-before-GREEN; CI and normal runs never set these,
# so they default to the real scripts under test.
CLAIM_SCRIPT = Path(os.environ.get("CLOSE_CLAIM_SCRIPT", str(ROOT / "skills" / "close" / "claim-todo.ps1")))
COMPLETE_SCRIPT = Path(os.environ.get("CLOSE_COMPLETE_SCRIPT", str(ROOT / "skills" / "close" / "complete-todo.ps1")))
TIMEOUT_SECONDS = 60

fails = []


def run_file(script: Path, *args: str) -> subprocess.CompletedProcess:
    """Invoke via -File with an explicit argv array - each element binds as
    one literal string, bypassing PowerShell's own command-line tokenizer.
    This is the "quoted" call shape: safe for any test that must NOT trigger
    the numeric-literal-array parsing this todo is about.
    """
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(script), *args],
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
    )


def run_command_text(command: str) -> subprocess.CompletedProcess:
    """Invoke via -Command with a literal PowerShell source string, so an
    unquoted comma list inside it goes through PowerShell's real expression
    parser - the only way to actually reproduce todo 1024's root cause.
    """
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
    )


def get_start_ticks(pid: int) -> int:
    """Query this machine's own record of a live pid's process start time,
    the same identity reserve-todo-id.ps1 and (after this todo) claim-todo.ps1
    use to disambiguate a pid from a later, unrelated process that inherits
    the same number once Windows recycles it.
    """
    proc = run_command_text(f"(Get-Process -Id {pid}).StartTime.Ticks")
    return int(proc.stdout.strip())


def write_claim(path: Path, *, pid: int, start_ticks: int | None, age_hours: float) -> None:
    """Write a claim file by hand (not via the script under test) so the
    staleness-reclaim path can be exercised with a controlled pid/start-ticks/
    age combination, then back-date its mtime past the 4h threshold.
    """
    lines = ["session: other-session", f"pid: {pid}"]
    if start_ticks is not None:
        lines.append(f"procStartTicks: {start_ticks}")
    lines.append("started: 2020-01-01T00:00:00.0000000Z")
    path.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    old = time.time() - age_hours * 3600
    os.utime(path, (old, old))


def make_backlog(tmpdir: Path, *filenames: str) -> Path:
    repo = tmpdir
    todos = repo / ".claude" / "todos"
    todos.mkdir(parents=True)
    for name in filenames:
        (todos / name).write_text(f"# {name}\n\n## Acceptance\n\n- done\n", encoding="utf-8")
    return repo


def claims_dir(repo: Path) -> Path:
    return repo / ".claude" / "todos" / ".claims"


def done_dir(repo: Path) -> Path:
    return repo / ".claude" / "todos" / "done"


# --- Test A: single padded id - no-regression case for both scripts ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "07-alpha.md")

    proc = run_file(CLAIM_SCRIPT, "-Id", "07", "-RepoRoot", str(repo))
    ok = proc.returncode == 0 and (claims_dir(repo) / "07.claim").exists()
    if not _testlib.report(ok, f"single padded id writes 07.claim (rc={proc.returncode}, out={proc.stdout!r})"):
        fails.append("single-id claim")

    proc = run_file(COMPLETE_SCRIPT, "-Id", "07", "-RepoRoot", str(repo))
    ok = (
        proc.returncode == 0
        and not (claims_dir(repo) / "07.claim").exists()
        and (done_dir(repo) / "07-alpha.md").exists()
        and "no claim on record" not in proc.stdout.lower()
    )
    if not _testlib.report(ok, f"single padded id completes cleanly, no false warning (out={proc.stdout!r})"):
        fails.append("single-id complete")


# --- Test B: quoted batch preserves padding and completes cleanly (1024 fix) ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "08-beta.md", "20-gamma.md")

    proc = run_file(CLAIM_SCRIPT, "-Id", "08,20", "-RepoRoot", str(repo))
    c = claims_dir(repo)
    ok = proc.returncode == 0 and (c / "08.claim").exists() and (c / "20.claim").exists()
    if not _testlib.report(ok, f"quoted batch writes 08.claim and 20.claim (out={proc.stdout!r})"):
        fails.append("quoted batch claim")

    proc = run_file(COMPLETE_SCRIPT, "-Id", "08", "-RepoRoot", str(repo))
    ok = (
        proc.returncode == 0
        and "Removed claim 08.claim" in proc.stdout
        and not (c / "08.claim").exists()
        and (c / "20.claim").exists()
        and "no claim on record" not in proc.stdout.lower()
    )
    if not _testlib.report(ok, f"completing 08 releases only 08.claim, no false warning (out={proc.stdout!r})"):
        fails.append("quoted batch complete")


# --- Test C: the real PowerShell parsing quirk strips padding on write;
# complete-todo.ps1 must still find and release the resulting unpadded claim
# when later called with the ORIGINAL padded id (todo 1024's actual defect:
# the leaked claim + false warning, not the unfixable upstream stripping). ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "08-beta.md", "20-gamma.md")
    repo_arg = str(repo).replace("'", "''")
    script_arg = str(CLAIM_SCRIPT).replace("'", "''")

    proc = run_command_text(f"& '{script_arg}' -Id 08,20 -RepoRoot '{repo_arg}'")
    c = claims_dir(repo)
    # This is PowerShell's own confirmed behavior, not a defect: an unquoted
    # numeric comma list is parsed as an int array, so "08" arrives as "8".
    stripped = proc.returncode == 0 and (c / "8.claim").exists() and not (c / "08.claim").exists()
    if not _testlib.report(stripped, f"unquoted batch reproduces PowerShell's own padding strip -> 8.claim (out={proc.stdout!r})"):
        fails.append("unquoted batch reproduction")

    # The caller still refers to the id the way they originally typed it.
    proc = run_file(COMPLETE_SCRIPT, "-Id", "08", "-RepoRoot", str(repo))
    ok = (
        proc.returncode == 0
        and "Removed claim 8.claim" in proc.stdout
        and not (c / "8.claim").exists()
        and (c / "20.claim").exists()
        and "no claim on record" not in proc.stdout.lower()
    )
    if not _testlib.report(ok, f"complete-todo.ps1 -Id 08 still finds and releases the unpadded 8.claim (out={proc.stdout!r})"):
        fails.append("complete finds unpadded claim")


# --- Test D: a batch mixing a padded bare id and a slug-disambiguated stem
# claims and releases both (Acceptance item 4) ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "08-beta.md", "20-gamma.md", "20-delta.md")

    proc = run_file(CLAIM_SCRIPT, "-Id", "08,20-delta", "-RepoRoot", str(repo))
    c = claims_dir(repo)
    ok = proc.returncode == 0 and (c / "08.claim").exists() and (c / "20-delta.claim").exists()
    if not _testlib.report(ok, f"mixed padded-id + slug-stem batch claims both (out={proc.stdout!r})"):
        fails.append("mixed batch claim")

    proc1 = run_file(COMPLETE_SCRIPT, "-Id", "08", "-RepoRoot", str(repo))
    proc2 = run_file(COMPLETE_SCRIPT, "-Id", "20", "-Slug", "delta", "-RepoRoot", str(repo))
    ok = (
        proc1.returncode == 0 and proc2.returncode == 0
        and not (c / "08.claim").exists() and not (c / "20-delta.claim").exists()
        and (c / "20-gamma.claim").exists() is False  # never claimed, never created
    )
    if not _testlib.report(ok, f"both release cleanly (out1={proc1.stdout!r}, out2={proc2.stdout!r})"):
        fails.append("mixed batch complete")


# --- Test E (todo 1015): complete-todo.ps1 rejects a batch -Id with the real
# cause, not a misleading "no todo file matching" message ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "07-alpha.md", "08-beta.md")

    proc = run_file(COMPLETE_SCRIPT, "-Id", "07,08", "-RepoRoot", str(repo))
    combined = proc.stdout + proc.stderr
    ok = (
        proc.returncode != 0
        and "no batch form" in combined.lower()
        and "no todo file matching" not in combined.lower()
    )
    if not _testlib.report(ok, f"batch -Id rejected with the real-cause message (rc={proc.returncode}, out={combined!r})"):
        fails.append("batch rejection message")

    # No-regression: the single-id form these six-todo sessions actually use
    # still works after the up-front comma check.
    proc = run_file(COMPLETE_SCRIPT, "-Id", "07", "-RepoRoot", str(repo))
    ok = proc.returncode == 0 and (done_dir(repo) / "07-alpha.md").exists()
    if not _testlib.report(ok, f"single id still completes after the batch-rejection check (out={proc.stdout!r})"):
        fails.append("single-id still works")


# --- Test F (todo 1083): a claim file names a pid that IS alive on this
# machine, but its recorded start time does NOT match that pid's actual
# start time - the shape a recycled pid takes once an unrelated process
# inherits the number. Past the 4h mtime threshold, this must reclaim. ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "09-alpha.md")
    c = claims_dir(repo)
    c.mkdir(parents=True)
    my_pid = os.getpid()
    my_start_ticks = get_start_ticks(my_pid)
    mismatching_ticks = my_start_ticks + 1  # alive pid, wrong identity
    write_claim(c / "09.claim", pid=my_pid, start_ticks=mismatching_ticks, age_hours=5)

    proc = run_file(CLAIM_SCRIPT, "-Id", "09", "-RepoRoot", str(repo))
    # Reclaim overwrites the claim with the caller's own session/pid, so the
    # stale marker ("other-session", written by write_claim) must be gone.
    ok = (
        proc.returncode == 0
        and "reclaimed" in proc.stdout.lower()
        and "other-session" not in (c / "09.claim").read_text(encoding="utf-8")
    )
    if not _testlib.report(ok, f"alive pid with mismatching start time is reclaimed past 4h (rc={proc.returncode}, out={proc.stdout!r})"):
        fails.append("mismatched start-time reclaim (1083)")


# --- Test G (todo 1083): a claim file names a pid that IS alive AND whose
# recorded start time matches - a genuinely live claim. Must never be
# reclaimed, no matter how old its mtime is. ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "10-alpha.md")
    c = claims_dir(repo)
    c.mkdir(parents=True)
    my_pid = os.getpid()
    my_start_ticks = get_start_ticks(my_pid)
    write_claim(c / "10.claim", pid=my_pid, start_ticks=my_start_ticks, age_hours=5)

    proc = run_file(CLAIM_SCRIPT, "-Id", "10", "-RepoRoot", str(repo))
    ok = (
        proc.returncode == 1
        and "not stale" in proc.stdout.lower()
        and (c / "10.claim").read_text(encoding="utf-8").find("session: other-session") != -1
    )
    if not _testlib.report(ok, f"genuinely live claim (matching start time) is never reclaimed (rc={proc.returncode}, out={proc.stdout!r})"):
        fails.append("genuine live claim never reclaimed (1083)")


# --- Test H (todo 1083): a legacy claim with no procStartTicks field at all
# falls back to the old pid-only check - alive pid, old mtime, still NOT
# stale (same behavior as before this todo, for a claim written before the
# field existed). ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "11-alpha.md")
    c = claims_dir(repo)
    c.mkdir(parents=True)
    my_pid = os.getpid()
    write_claim(c / "11.claim", pid=my_pid, start_ticks=None, age_hours=5)

    proc = run_file(CLAIM_SCRIPT, "-Id", "11", "-RepoRoot", str(repo))
    ok = (
        proc.returncode == 1
        and "not stale" in proc.stdout.lower()
        and (c / "11.claim").read_text(encoding="utf-8").find("session: other-session") != -1
    )
    if not _testlib.report(ok, f"legacy claim with no procStartTicks keeps old pid-only check (rc={proc.returncode}, out={proc.stdout!r})"):
        fails.append("legacy claim backward compat (1083)")


sys.exit(_testlib.summarize(fails, style="count"))
