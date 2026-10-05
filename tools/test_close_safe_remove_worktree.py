"""Self-test for safe-remove-worktree.ps1's registration guard and the
partly-succeeded-force-removal diagnosis it gained for todo 981.

Run directly: python tools/test_close_safe_remove_worktree.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Drives the real script via powershell.exe against real git repos/worktrees
built under tempfile.TemporaryDirectory() - never a repo this session does
not own.

todo 981's reproduction (confirmed live this session, not assumed): holding
a file open under an exclusive lock inside a worktree, then
`git worktree remove --force`, makes git delete the worktree's own ".git"
file and drop the entry from `git worktree list` BEFORE it discovers the
directory still isn't empty and fails - so by the time anything can inspect
the leftover, no git-side fingerprint survives to tell it apart from an
arbitrary directory. That ruled out widening the registration guard (no
signal to widen it on); the fix actually shipped is a diagnosable refusal
message naming the failure mode and the manual recovery, with the guard's
behavior otherwise UNCHANGED - proven below by the guard still refusing a
real arbitrary directory with a reparse point in it, and the reparse-point
protection still firing for a registered worktree.
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

SCRIPT = Path(os.environ.get(
    "CLOSE_SAFE_REMOVE_SCRIPT", str(ROOT / "skills" / "close" / "safe-remove-worktree.ps1")
))
TIMEOUT_SECONDS = 60

# The GitHub Windows runner's TEMP is an 8.3 short path (C:\Users\RUNNER~1\...)
# while `git worktree list` reports the long form, so the script's registration
# check failed every worktree built there. resolve() expands the short name.
tempfile.tempdir = str(Path(tempfile.gettempdir()).resolve())

fails = []


def run_script(worktree_path: Path, repo_root: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT),
         "-WorktreePath", str(worktree_path), "-RepoRoot", str(repo_root), *extra],
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
    )


def git(*args: str, cwd: Path = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd) if cwd else None,
                           capture_output=True, text=True, timeout=TIMEOUT_SECONDS)


def make_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    git("init", "-q", cwd=repo)
    git("config", "user.email", "t@t.com", cwd=repo)
    git("config", "user.name", "t", cwd=repo)
    (repo / "file.txt").write_text("hello\n", encoding="utf-8")
    git("add", "file.txt", cwd=repo)
    git("commit", "-qm", "init", cwd=repo)
    return repo


def add_worktree(repo: Path, branch: str, path: Path) -> None:
    git("branch", branch, cwd=repo)
    proc = git("worktree", "add", str(path), branch, cwd=repo)
    assert proc.returncode == 0, proc.stderr


# --- Test 1: happy path, no lock - removes cleanly, main checkout untouched ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_repo(Path(tmp))
    wt = Path(tmp) / "wt1"
    add_worktree(repo, "wt1", wt)

    proc = run_script(wt, repo)
    ok = proc.returncode == 0 and not wt.exists()
    if not _testlib.report(ok, f"plain worktree removes cleanly (rc={proc.returncode}, out={proc.stdout!r})"):
        fails.append("happy path")

    status = git("status", "--short", cwd=repo)
    if not _testlib.report(status.stdout.strip() == "", f"main checkout stays clean (status={status.stdout!r})"):
        fails.append("happy path status clean")


# --- Test 2: refuses the main checkout itself ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_repo(Path(tmp))
    proc = run_script(repo, repo)
    combined = proc.stdout + proc.stderr
    ok = proc.returncode != 0 and "refusing to remove the main checkout" in combined
    if not _testlib.report(ok, f"refuses WorktreePath == RepoRoot (out={combined!r})"):
        fails.append("refuse main checkout")


# --- Test 3: refuses an arbitrary directory (never registered), even one
# containing a real reparse point - the exact case the registration guard
# exists to stop, proven with an actual junction, not by reading the code ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_repo(Path(tmp))
    arbitrary = Path(tmp) / "not-a-worktree"
    arbitrary.mkdir()
    target = Path(tmp) / "junction-target"
    target.mkdir()
    sentinel = target / "sentinel.txt"
    sentinel.write_text("do not touch\n", encoding="utf-8")
    link = arbitrary / "linked"
    mk = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                         capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    assert link.is_dir(), mk.stdout + mk.stderr

    proc = run_script(arbitrary, repo)
    combined = proc.stdout + proc.stderr
    ok = (
        proc.returncode != 0
        and "not a worktree registered" in combined
        and sentinel.exists()
        and sentinel.read_text(encoding="utf-8") == "do not touch\n"
    )
    if not _testlib.report(ok, f"refuses an arbitrary directory with a real reparse point, junction target untouched (out={combined!r})"):
        fails.append("refuse arbitrary dir with reparse point")


# --- Test 4: a REGISTERED worktree's reparse point is unlinked (not
# followed) before removal - the junction target survives ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_repo(Path(tmp))
    wt = Path(tmp) / "wt4"
    add_worktree(repo, "wt4", wt)
    target = Path(tmp) / "junction-target-4"
    target.mkdir()
    sentinel = target / "sentinel.txt"
    sentinel.write_text("do not touch\n", encoding="utf-8")
    link = wt / "linked"
    mk = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                         capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
    assert link.is_dir(), mk.stdout + mk.stderr

    proc = run_script(wt, repo)
    ok = (
        proc.returncode == 0
        and not wt.exists()
        and sentinel.exists()
        and sentinel.read_text(encoding="utf-8") == "do not touch\n"
    )
    if not _testlib.report(ok, f"registered worktree's junction unlinked, target untouched, worktree removed (out={proc.stdout!r})"):
        fails.append("reparse point protection on registered worktree")


# --- Test 5 (todo 981): reproduce the partly-succeeded force removal through
# THIS script (not raw git), then prove the follow-up call against the now-
# unregistered leftover is diagnosable, not a bare "not a worktree" ---

with tempfile.TemporaryDirectory() as tmp:
    repo = make_repo(Path(tmp))
    wt = Path(tmp) / "wt5"
    add_worktree(repo, "wt5", wt)
    locked_path = wt / "file.txt"

    handle = open(locked_path, "rb")
    try:
        proc1 = run_script(wt, repo)
        ok1 = proc1.returncode != 0 and wt.exists()
        if not _testlib.report(ok1, f"first call fails to fully remove while the file is locked (rc={proc1.returncode}, out={proc1.stdout + proc1.stderr!r})"):
            fails.append("981: first call leaves leftover")

        list_after = git("worktree", "list", "--porcelain", cwd=repo)
        deregistered = str(wt.resolve()) not in list_after.stdout.replace("/", "\\")
        if not _testlib.report(deregistered, f"git deregistered the worktree despite the failed removal (list={list_after.stdout!r})"):
            fails.append("981: deregistered")

        proc2 = run_script(wt, repo)
        combined2 = proc2.stdout + proc2.stderr
        ok2 = (
            proc2.returncode != 0
            and "not a worktree registered" in combined2
            and "todo 981" in combined2
            and wt.exists()
        )
        if not _testlib.report(ok2, f"follow-up call on the leftover explains the failure mode instead of a bare refusal (out={combined2!r})"):
            fails.append("981: diagnosable refusal")
    finally:
        handle.close()

    # Teardown: lock released, directory is now a normal (if orphaned) one.
    import shutil
    shutil.rmtree(wt, ignore_errors=True)


sys.exit(_testlib.summarize(fails, style="count"))
