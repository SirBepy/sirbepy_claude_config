"""Self-test for claim-todo.ps1 / complete-todo.ps1: batch-id handling and the
device-prefixed id scheme (`<label>-<NNNN>`).

Run directly: python tools/test_close_claim_complete.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Drives the real scripts via powershell.exe against scratch backlog directories
under tempfile.TemporaryDirectory() - never the real .claude/todos/. Every run
points the scripts at a throwaway label file (CLAUDE_DEVICE_LABEL_FILE), so no
case reads or writes the real ~/.claude/device-label.

Covers these todos:

- 1024 (batch claim strips zero padding): the confirmed root cause is
  PowerShell's OWN parser, not this repo's code - an unquoted `-Id 08,20`
  is tokenized as an array of numeric literals before claim-todo.ps1 ever
  runs, so "08" arrives as "8" with no way for the script to recover the
  padding after the fact. That loss is real PowerShell behavior (reproduced
  on purpose in test C). What was broken is whether complete-todo.ps1 still
  finds and releases the resulting claim; claim names are now always the
  canonical 4-digit `pc-0008.claim`, so padding no longer matters.

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

- Device-prefixed ids: tests I-P cover bare-number resolution (this device
  first, a unique other label, ambiguity), legacy bare-numeric files and
  claim names, the PLAN.md prune across every spelling of an id, and the
  loud failure when ~/.claude/device-label is missing.
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

_LABEL_DIR = tempfile.TemporaryDirectory()
LABEL_FILE = Path(_LABEL_DIR.name) / "device-label"
LABEL_FILE.write_text("pc\n", encoding="utf-8")
MISSING_LABEL_FILE = Path(_LABEL_DIR.name) / "no-such-label-file"
CHILD_ENV = dict(os.environ, CLAUDE_DEVICE_LABEL_FILE=str(LABEL_FILE))

fails = []


def run_file(script: Path, *args: str, env: "dict | None" = None) -> subprocess.CompletedProcess:
    """Invoke via -File with an explicit argv array - each element binds as
    one literal string, bypassing PowerShell's own command-line tokenizer.
    This is the "quoted" call shape: safe for any test that must NOT trigger
    the numeric-literal-array parsing todo 1024 is about.
    """
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(script), *args],
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS, env=env or CHILD_ENV,
    )


def run_command_text(command: str) -> subprocess.CompletedProcess:
    """Invoke via -Command with a literal PowerShell source string, so an
    unquoted comma list inside it goes through PowerShell's real expression
    parser - the only way to actually reproduce todo 1024's root cause.
    """
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS, env=CHILD_ENV,
    )


def get_start_ticks(pid: int) -> int:
    """Query this machine's own record of a live pid's process start time,
    the same identity reserve-todo-id.ps1 and claim-todo.ps1 use to
    disambiguate a pid from a later, unrelated process that inherits the
    same number once Windows recycles it.
    """
    proc = run_command_text(f"(Get-Process -Id {pid}).StartTime.Ticks")
    return int(proc.stdout.strip())


def write_claim(path: Path, *, pid: int, start_ticks: "int | None", age_hours: float) -> None:
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


def plan_path(repo: Path) -> Path:
    return repo / ".claude" / "todos" / "PLAN.md"


def check(label: str, ok: bool) -> None:
    if not _testlib.report(ok, label):
        fails.append(label)


# --- Test A: single padded id - no-regression case for both scripts ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "pc-0007-alpha.md")

    proc = run_file(CLAIM_SCRIPT, "-Id", "pc-0007", "-RepoRoot", str(repo))
    ok = proc.returncode == 0 and (claims_dir(repo) / "pc-0007.claim").exists()
    check(f"single full id writes pc-0007.claim (rc={proc.returncode}, out={proc.stdout!r})", ok)

    proc = run_file(COMPLETE_SCRIPT, "-Id", "pc-0007", "-RepoRoot", str(repo))
    ok = (
        proc.returncode == 0
        and not (claims_dir(repo) / "pc-0007.claim").exists()
        and (done_dir(repo) / "pc-0007-alpha.md").exists()
        and "no claim on record" not in proc.stdout.lower()
    )
    check(f"single full id completes cleanly, no false warning (out={proc.stdout!r})", ok)


# --- Test B: quoted batch preserves the id as typed and completes cleanly (1024 fix) ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "pc-0008-beta.md", "pc-0020-gamma.md")

    proc = run_file(CLAIM_SCRIPT, "-Id", "08,20", "-RepoRoot", str(repo))
    c = claims_dir(repo)
    ok = proc.returncode == 0 and (c / "pc-0008.claim").exists() and (c / "pc-0020.claim").exists()
    check(f"quoted bare-number batch writes pc-0008.claim and pc-0020.claim (out={proc.stdout!r})", ok)

    proc = run_file(COMPLETE_SCRIPT, "-Id", "08", "-RepoRoot", str(repo))
    ok = (
        proc.returncode == 0
        and "Removed claim pc-0008.claim" in proc.stdout
        and not (c / "pc-0008.claim").exists()
        and (c / "pc-0020.claim").exists()
        and "no claim on record" not in proc.stdout.lower()
    )
    check(f"completing 08 releases only pc-0008.claim, no false warning (out={proc.stdout!r})", ok)


# --- Test C: the real PowerShell parsing quirk strips padding before the script
# runs; with canonical claim names the stripped id still lands on pc-0008.claim and
# complete-todo.ps1 releases it when later called with the ORIGINAL padded id. ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "pc-0008-beta.md", "pc-0020-gamma.md")
    repo_arg = str(repo).replace("'", "''")
    script_arg = str(CLAIM_SCRIPT).replace("'", "''")

    proc = run_command_text(f"& '{script_arg}' -Id 08,20 -RepoRoot '{repo_arg}'")
    c = claims_dir(repo)
    check(
        f"unquoted batch (PowerShell strips the padding itself) still claims canonical pc-0008.claim (out={proc.stdout!r})",
        proc.returncode == 0 and (c / "pc-0008.claim").exists() and (c / "pc-0020.claim").exists()
        and "pre-split" in proc.stdout,
    )

    proc = run_file(COMPLETE_SCRIPT, "-Id", "08", "-RepoRoot", str(repo))
    ok = (
        proc.returncode == 0
        and "Removed claim pc-0008.claim" in proc.stdout
        and not (c / "pc-0008.claim").exists()
        and (c / "pc-0020.claim").exists()
        and "no claim on record" not in proc.stdout.lower()
    )
    check(f"complete-todo.ps1 -Id 08 finds and releases the claim (out={proc.stdout!r})", ok)


# --- Test D: a batch mixing a bare number and a slug-disambiguated stem
# claims and releases both (Acceptance item 4) ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "pc-0008-beta.md", "pc-0020-gamma.md", "pc-0020-delta.md")

    proc = run_file(CLAIM_SCRIPT, "-Id", "08,pc-0020-delta", "-RepoRoot", str(repo))
    c = claims_dir(repo)
    ok = proc.returncode == 0 and (c / "pc-0008.claim").exists() and (c / "pc-0020-delta.claim").exists()
    check(f"mixed bare-number + slug-stem batch claims both (out={proc.stdout!r})", ok)

    proc1 = run_file(COMPLETE_SCRIPT, "-Id", "08", "-RepoRoot", str(repo))
    proc2 = run_file(COMPLETE_SCRIPT, "-Id", "pc-0020", "-Slug", "delta", "-RepoRoot", str(repo))
    ok = (
        proc1.returncode == 0 and proc2.returncode == 0
        and not (c / "pc-0008.claim").exists() and not (c / "pc-0020-delta.claim").exists()
        and (c / "pc-0020-gamma.claim").exists() is False  # never claimed, never created
    )
    check(f"both release cleanly (out1={proc1.stdout!r}, out2={proc2.stdout!r})", ok)


# --- Test E (todo 1015): complete-todo.ps1 rejects a batch -Id with the real
# cause, not a misleading "no todo file matching" message ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "pc-0007-alpha.md", "pc-0008-beta.md")

    proc = run_file(COMPLETE_SCRIPT, "-Id", "07,08", "-RepoRoot", str(repo))
    combined = proc.stdout + proc.stderr
    ok = (
        proc.returncode != 0
        and "no batch form" in combined.lower()
        and "no todo file matching" not in combined.lower()
    )
    check(f"batch -Id rejected with the real-cause message (rc={proc.returncode}, out={combined!r})", ok)

    # No-regression: the single-id form these six-todo sessions actually use
    # still works after the up-front comma check.
    proc = run_file(COMPLETE_SCRIPT, "-Id", "07", "-RepoRoot", str(repo))
    ok = proc.returncode == 0 and (done_dir(repo) / "pc-0007-alpha.md").exists()
    check(f"single id still completes after the batch-rejection check (out={proc.stdout!r})", ok)


# --- Test F (todo 1083): a claim file names a pid that IS alive on this
# machine, but its recorded start time does NOT match that pid's actual
# start time - the shape a recycled pid takes once an unrelated process
# inherits the number. Past the 4h mtime threshold, this must reclaim. ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "pc-0009-alpha.md")
    c = claims_dir(repo)
    c.mkdir(parents=True)
    my_pid = os.getpid()
    my_start_ticks = get_start_ticks(my_pid)
    mismatching_ticks = my_start_ticks + 1  # alive pid, wrong identity
    write_claim(c / "pc-0009.claim", pid=my_pid, start_ticks=mismatching_ticks, age_hours=5)

    proc = run_file(CLAIM_SCRIPT, "-Id", "pc-0009", "-RepoRoot", str(repo))
    # Reclaim overwrites the claim with the caller's own session/pid, so the
    # stale marker ("other-session", written by write_claim) must be gone.
    ok = (
        proc.returncode == 0
        and "reclaimed" in proc.stdout.lower()
        and "other-session" not in (c / "pc-0009.claim").read_text(encoding="utf-8")
    )
    check(f"alive pid with mismatching start time is reclaimed past 4h (rc={proc.returncode}, out={proc.stdout!r})", ok)


# --- Test G (todo 1083): a claim file names a pid that IS alive AND whose
# recorded start time matches - a genuinely live claim. Must never be
# reclaimed, no matter how old its mtime is. ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "pc-0010-alpha.md")
    c = claims_dir(repo)
    c.mkdir(parents=True)
    my_pid = os.getpid()
    my_start_ticks = get_start_ticks(my_pid)
    write_claim(c / "pc-0010.claim", pid=my_pid, start_ticks=my_start_ticks, age_hours=5)

    proc = run_file(CLAIM_SCRIPT, "-Id", "pc-0010", "-RepoRoot", str(repo))
    ok = (
        proc.returncode == 1
        and "not stale" in proc.stdout.lower()
        and (c / "pc-0010.claim").read_text(encoding="utf-8").find("session: other-session") != -1
    )
    check(f"genuinely live claim (matching start time) is never reclaimed (rc={proc.returncode}, out={proc.stdout!r})", ok)


# --- Test H (todo 1083): a legacy claim with no procStartTicks field at all
# falls back to the old pid-only check - alive pid, old mtime, still NOT
# stale (same behavior as before this todo, for a claim written before the
# field existed). ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "pc-0011-alpha.md")
    c = claims_dir(repo)
    c.mkdir(parents=True)
    my_pid = os.getpid()
    write_claim(c / "pc-0011.claim", pid=my_pid, start_ticks=None, age_hours=5)

    proc = run_file(CLAIM_SCRIPT, "-Id", "pc-0011", "-RepoRoot", str(repo))
    ok = (
        proc.returncode == 1
        and "not stale" in proc.stdout.lower()
        and (c / "pc-0011.claim").read_text(encoding="utf-8").find("session: other-session") != -1
    )
    check(f"legacy claim with no procStartTicks keeps old pid-only check (rc={proc.returncode}, out={proc.stdout!r})", ok)


# --- Test I: a bare number resolves to THIS device's label first, even when another
# device has the same number; a full id reaches the other one ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "pc-0050-mine.md", "mac-0050-theirs.md")
    c = claims_dir(repo)

    proc = run_file(CLAIM_SCRIPT, "-Id", "50", "-RepoRoot", str(repo))
    check(
        f"bare 50 claims this device's pc-0050 and not mac-0050 (out={proc.stdout!r})",
        proc.returncode == 0 and (c / "pc-0050.claim").exists() and not (c / "mac-0050.claim").exists(),
    )

    proc = run_file(CLAIM_SCRIPT, "-Id", "mac-50", "-RepoRoot", str(repo))
    check(
        f"an unpadded full id mac-50 reaches the other device's file as mac-0050.claim (out={proc.stdout!r})",
        proc.returncode == 0 and (c / "mac-0050.claim").exists(),
    )

    proc = run_file(COMPLETE_SCRIPT, "-Id", "50", "-RepoRoot", str(repo))
    check(
        f"completing bare 50 archives only pc-0050-mine.md (out={proc.stdout!r})",
        proc.returncode == 0 and (done_dir(repo) / "pc-0050-mine.md").exists()
        and (repo / ".claude" / "todos" / "mac-0050-theirs.md").exists()
        and not (c / "pc-0050.claim").exists() and (c / "mac-0050.claim").exists(),
    )


# --- Test J: when this device has no such number, a unique match on another label is accepted ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "mac-0060-only-theirs.md")
    proc = run_file(CLAIM_SCRIPT, "-Id", "60", "-RepoRoot", str(repo))
    check(
        f"bare 60 with only mac-0060 present claims mac-0060 (out={proc.stdout!r})",
        proc.returncode == 0 and (claims_dir(repo) / "mac-0060.claim").exists(),
    )


# --- Test K: a bare number on several other labels is an error naming every candidate ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "mac-0070-a.md", "mac2-0070-b.md")
    proc = run_file(CLAIM_SCRIPT, "-Id", "70", "-RepoRoot", str(repo))
    combined = proc.stdout + proc.stderr
    check(
        f"ambiguous bare 70 exits 2 and names mac-0070 and mac2-0070 (rc={proc.returncode}, out={combined!r})",
        proc.returncode == 2 and "mac-0070" in combined and "mac2-0070" in combined
        and not any(claims_dir(repo).glob("*.claim")),
    )

    proc = run_file(COMPLETE_SCRIPT, "-Id", "70", "-RepoRoot", str(repo))
    combined = proc.stdout + proc.stderr
    check(
        f"complete-todo.ps1 refuses the same ambiguity and moves nothing (rc={proc.returncode})",
        proc.returncode != 0 and "mac2-0070" in combined and not done_dir(repo).exists(),
    )


# --- Test L: legacy bare-numeric files and claim names keep resolving, read as label pc ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "0123-legacy-todo.md", "0124-legacy-two.md")
    c = claims_dir(repo)

    proc = run_file(CLAIM_SCRIPT, "-Id", "123", "-RepoRoot", str(repo))
    check(
        f"claiming legacy 0123-legacy-todo.md writes the canonical pc-0123.claim (out={proc.stdout!r})",
        proc.returncode == 0 and (c / "pc-0123.claim").exists(),
    )

    proc = run_file(COMPLETE_SCRIPT, "-Id", "pc-123", "-RepoRoot", str(repo))
    check(
        f"pc-123 completes the legacy file under its own name and releases the claim (out={proc.stdout!r})",
        proc.returncode == 0 and (done_dir(repo) / "0123-legacy-todo.md").exists() and not (c / "pc-0123.claim").exists(),
    )

    # A claim a still-running pre-migration session wrote under its bare name.
    write_claim(c / "124.claim", pid=os.getpid(), start_ticks=get_start_ticks(os.getpid()), age_hours=0.1)
    proc = run_file(CLAIM_SCRIPT, "-Id", "pc-0124", "-RepoRoot", str(repo))
    check(
        f"a live bare-named 124.claim blocks a second claim on pc-0124 (rc={proc.returncode}, out={proc.stdout!r})",
        proc.returncode == 1 and "already claimed" in proc.stdout and not (c / "pc-0124.claim").exists(),
    )

    proc = run_file(COMPLETE_SCRIPT, "-Id", "124", "-RepoRoot", str(repo))
    check(
        f"completing releases the bare-named 124.claim too (out={proc.stdout!r})",
        proc.returncode == 0 and "Removed claim 124.claim" in proc.stdout and not (c / "124.claim").exists(),
    )


# --- Test M: the PLAN.md prune matches every spelling of an id, and only that id ---

PLAN_FIXTURE = "\n".join([
    "# Plan",
    "",
    "- [ ] pc-1407 - the target, canonical",
    "- [ ] pc-01407 - same id, extra padding",
    "- [ ] pc-1407 [P]",
    "- [ ] **pc-1407** - bold",
    "- [ ] `pc-1407` - backtick",
    "- [ ] pc-1407 - wrapped entry whose",
    "  continuation line carries no id",
    "- [ ] 1407 - legacy bare number",
    "- [ ] 01407 - legacy bare number, padded",
    "- [ ] mac-1407 - another device, same number: must survive",
    "- [ ] pc-14070 - a different number: must survive",
    "- [ ] pc-1408 - a different number: must survive",
    "- [ ] 1408 - a different legacy number: must survive",
    "",
])

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "pc-1407-the-target.md")
    plan_path(repo).write_text(PLAN_FIXTURE, encoding="utf-8")

    proc = run_file(COMPLETE_SCRIPT, "-Id", "pc-1407", "-RepoRoot", str(repo))
    plan = plan_path(repo).read_text(encoding="utf-8")
    pruned = ["canonical", "extra padding", "[P]", "bold", "backtick", "wrapped entry", "continuation line",
              "legacy bare number"]
    kept = ["mac-1407", "pc-14070", "pc-1408", "- [ ] 1408"]
    check(
        f"PLAN prune drops every spelling of pc-1407 incl. the wrapped continuation (rc={proc.returncode}, plan={plan!r})",
        proc.returncode == 0 and not any(x in plan for x in pruned),
    )
    check(
        f"PLAN prune keeps mac-1407, pc-14070, pc-1408 and legacy 1408 (plan={plan!r})",
        all(x in plan for x in kept),
    )

# A non-pc label never prunes a bare legacy line (bare numbers belong to pc only).
with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "mac-0031-theirs.md")
    plan_path(repo).write_text("- [ ] 31 - legacy pc line\n- [ ] mac-0031 - the target\n", encoding="utf-8")
    proc = run_file(COMPLETE_SCRIPT, "-Id", "mac-31", "-RepoRoot", str(repo))
    plan = plan_path(repo).read_text(encoding="utf-8")
    check(
        f"completing mac-0031 prunes mac-0031 and leaves the bare pc line (plan={plan!r})",
        proc.returncode == 0 and "mac-0031" not in plan and "legacy pc line" in plan,
    )


# --- Test N: a repeat completion reports "already completed" without error, by full id ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "pc-0080-once.md")
    run_file(COMPLETE_SCRIPT, "-Id", "pc-0080", "-RepoRoot", str(repo))
    proc = run_file(COMPLETE_SCRIPT, "-Id", "80", "-RepoRoot", str(repo))
    combined = proc.stdout + proc.stderr
    check(
        f"second completion of bare 80 reports pc-0080 already completed (rc={proc.returncode}, out={combined!r})",
        proc.returncode == 0 and "pc-0080 already completed" in combined,
    )


# --- Test O: a bare number needs the device label; a full id does not; the failure names the fix ---

missing_env = dict(os.environ, CLAUDE_DEVICE_LABEL_FILE=str(MISSING_LABEL_FILE))
with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "pc-0090-label-free.md")
    proc = run_file(CLAIM_SCRIPT, "-Id", "90", "-RepoRoot", str(repo), env=missing_env)
    combined = proc.stdout + proc.stderr
    check(
        f"bare id with no device-label fails loudly and claims nothing (rc={proc.returncode})",
        proc.returncode != 0 and "device-label" in combined and '"pc" or "mac"' in combined
        and not any(claims_dir(repo).glob("*.claim")),
    )

    proc = run_file(CLAIM_SCRIPT, "-Id", "pc-0090", "-RepoRoot", str(repo), env=missing_env)
    check(
        f"a full id needs no device-label (rc={proc.returncode}, out={proc.stdout!r})",
        proc.returncode == 0 and (claims_dir(repo) / "pc-0090.claim").exists(),
    )


# --- Test P: slug-bearing full stem still disambiguates a colliding id ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_backlog(Path(tmp), "pc-0095-first.md", "pc-0095-second.md")
    proc = run_file(CLAIM_SCRIPT, "-Id", "pc-0095", "-RepoRoot", str(repo))
    check(
        f"a colliding id without a slug is reported ambiguous (rc={proc.returncode}, out={proc.stdout!r})",
        proc.returncode == 2 and "Ambiguous" in proc.stdout and "pc-0095-first.md" in proc.stdout,
    )
    proc = run_file(CLAIM_SCRIPT, "-Id", "pc-95", "-Slug", "second", "-RepoRoot", str(repo))
    check(
        f"-Slug picks the sibling and names the claim pc-0095-second.claim (out={proc.stdout!r})",
        proc.returncode == 0 and (claims_dir(repo) / "pc-0095-second.claim").exists(),
    )


_LABEL_DIR.cleanup()
sys.exit(_testlib.summarize(fails, style="count"))
