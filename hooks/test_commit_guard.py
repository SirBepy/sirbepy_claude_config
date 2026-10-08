"""Self-test for commit-guard.py.

Run directly: python hooks/test_commit_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Covers is_git_commit_invocation's token-aware detection, then drives the
real guard.main() with a monkeypatched read_payload against a temp
MARKER_DIR/SESSION_MARKER_DIR - no subprocess, no live git, no network.
Per done/335's notes, marker-consume logic itself lives in
_hooklib.consume_fresh_marker and is exercised through the guard's own
constants (MARKER_GLOB, exclude_prefix) rather than re-testing _hooklib
directly. Deny-path assertions check only the exit code (2), never the
reworded bypass message (todo 463), so this suite stays decoupled from
prose.
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "commit-guard.py"
)

# --- is_git_commit_invocation: token-aware, not a string search ---

INVOCATION_CASES = [
    ("git commit -m 'fix'", True, "plain git commit"),
    ("git commit-graph write", False, "commit-graph is not commit"),
    ("git -C C:/repo commit -m 'x'", True, "git -C <path> commit, value flag skipped"),
    ("git commit --message 'a big commit here'", True, "commit text inside message is fine"),
    ("echo \"git commit\"", False, "git commit only inside a quoted string, one token"),
    ("npm run build && git commit -m 'x'", True, "chained after an unrelated command"),
    ("git status", False, "unrelated git subcommand"),
    ("git --grep=\"commit\" log", False, "commit only inside a flag value"),
]


def check_invocation(case) -> bool:
    command, expected, label = case
    got = guard.is_git_commit_invocation(command)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails = _testlib.run_cases(INVOCATION_CASES, check_invocation)

# --- is_commit_landing_invocation: also catches the commit-tree + update-ref
# path split-hunks.py's own design note (todo 1085) flags as a bypass: a raw
# shell command landing a commit this way must gate the same as `git commit`.

LANDING_CASES = [
    (
        "git commit-tree deadbeef -p HEAD -m 'x' && git update-ref refs/heads/master new old",
        True,
        "commit-tree + update-ref to a branch ref lands a commit, must gate",
    ),
    ("git commit-tree deadbeef -p HEAD -m 'x'", True, "commit-tree alone still creates a commit object"),
    ("git update-ref refs/heads/feature new old", True, "update-ref straight to a branch ref"),
    ("git update-ref HEAD new old", True, "update-ref straight to HEAD"),
    ("git commit -m 'x'", True, "plain git commit still matches via this entrypoint too"),
    ("git update-ref --stdin", False, "update-ref --stdin reads refs from input, no branch positional here"),
    ("git update-ref refs/notes/commits new old", False, "update-ref to a non-branch ref is unrelated"),
    ("git log", False, "unrelated read-only git subcommand"),
    ("git update-ref -d refs/heads/old-branch", True, "deleting a branch ref still mutates history pointers"),
    (
        "git update-ref refs/notes/x a && git update-ref refs/heads/master b",
        True,
        "a branch-moving update-ref chained after a notes one still lands a commit",
    ),
    (
        "git update-ref refs/notes/x a && git update-ref refs/notes/y b",
        False,
        "two chained non-branch update-refs stay ungated",
    ),
]


def check_landing(case) -> bool:
    command, expected, label = case
    got = guard.is_commit_landing_invocation(command)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(LANDING_CASES, check_landing)

# --- extract_commit_pathspec: `--` pathspec resolution, chain-operator aware ---

PATHSPEC_CASES = [
    ("git commit -m 'x' -- a.py b.py", ["a.py", "b.py"], "plain pathspec after --"),
    ("git commit -m 'x'", None, "no -- separator means no resolvable pathspec"),
    (
        "bash gate.sh a.py ; git commit -m 'x' -- a.py",
        ["a.py"],
        "pathspec resolves from the commit's own -- , ignoring what precedes it",
    ),
    (
        "bash gate.sh a.py && git commit -m 'x' -- a.py",
        ["a.py"],
        "same resolution for the && form",
    ),
    (
        "git commit -m 'x' -- a.py && echo done",
        ["a.py"],
        "a chain operator after the pathspec stops the scan, not swallowed as a path",
    ),
]


def check_pathspec(case) -> bool:
    command, expected, label = case
    tokens = guard._tokenize(command)
    got = guard.extract_commit_pathspec(tokens)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(PATHSPEC_CASES, check_pathspec)

# --- main() end to end, temp marker dirs only ---


def run_main(command: str, session_id: str = "", cwd: str = "") -> int:
    guard.read_payload = lambda: {"tool_input": {"command": command}, "session_id": session_id, "cwd": cwd}
    try:
        guard.main()
        return 0
    except SystemExit as e:
        return e.code


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir
    guard.SESSION_MARKER_DIR = tmpdir / ".session-markers"
    guard.SESSION_MARKER_DIR.mkdir(parents=True)

    label = "raw git commit with no marker at all is blocked"
    got = run_main("git commit -m 'x'", session_id="sess-1")
    if not _testlib.report(got == 2, f"{label} (got exit={got})"):
        fails.append(label)

    label = "a non-commit command needs no marker"
    got = run_main("git status", session_id="sess-1")
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)

    label = "a raw commit-tree + update-ref landing with no marker is blocked (todo 1085)"
    got = run_main(
        "git commit-tree deadbeef -p HEAD -m 'x' && git update-ref refs/heads/master new old",
        session_id="sess-1b",
    )
    if not _testlib.report(got == 2, f"{label} (got exit={got})"):
        fails.append(label)

    label = "a read-only update-ref to a non-branch ref needs no marker"
    got = run_main("git update-ref refs/notes/commits new old", session_id="sess-1c")
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)

    # Legacy per-commit marker: consumed on use.
    legacy_marker = tmpdir / ".commit-marker-abc123"
    legacy_marker.touch()
    label = "a fresh legacy .commit-marker is consumed and allows"
    got = run_main("git commit -m 'x'", session_id="sess-2")
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)
    label = "the legacy marker is deleted after being consumed"
    if not _testlib.report(not legacy_marker.exists(), label):
        fails.append(label)
    label = "the same session's next raw commit is blocked again, marker gone"
    got = run_main("git commit -m 'y'", session_id="sess-2")
    if not _testlib.report(got == 2, f"{label} (got exit={got})"):
        fails.append(label)

    # Session marker: never consumed, checked by exact session id.
    session_id = "sess-3"
    session_marker = guard.session_marker_path(session_id)
    session_marker.touch()
    label = "a session marker allows a commit for its exact session id"
    got = run_main("git commit -m 'x'", session_id=session_id)
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)
    label = "the session marker is NOT consumed, unlike the legacy one"
    if not _testlib.report(session_marker.exists(), label):
        fails.append(label)
    label = "a different session id does not see another session's marker"
    got = run_main("git commit -m 'x'", session_id="sess-4")
    if not _testlib.report(got == 2, f"{label} (got exit={got})"):
        fails.append(label)

    label = "a marked session's commit-tree + update-ref landing is allowed (split-hunks.py's own route stays unblocked)"
    got = run_main(
        "git commit-tree deadbeef -p HEAD -m 'x' && git update-ref refs/heads/master new old",
        session_id=session_id,
    )
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)

    # Legacy session marker fallback (pre todo-341 split location).
    legacy_session_id = "sess-5"
    legacy_session_marker = guard.legacy_session_marker_path(legacy_session_id)
    legacy_session_marker.touch()
    label = "a legacy-location session marker still allows its exact session"
    got = run_main("git commit -m 'x'", session_id=legacy_session_id)
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)

    # The legacy session marker's own filename must never satisfy the
    # legacy per-commit glob (exclude_prefix), or a live session marker
    # could be silently eaten by a stray raw commit from another session.
    label = "consume_fresh_marker excludes the legacy session-marker prefix"
    excluded = guard.consume_fresh_marker(
        tmpdir,
        guard.MARKER_GLOB,
        guard.FRESHNESS_SECONDS,
        exclude_prefix=guard.LEGACY_SESSION_MARKER_PREFIX,
    )
    if not _testlib.report(excluded is False, label):
        fails.append(label)

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir
    guard.SESSION_MARKER_DIR = tmpdir / ".session-markers"
    guard.SESSION_MARKER_DIR.mkdir(parents=True)

    saved_bypass = os.environ.pop(guard.OVERRIDE_ENV, None)
    os.environ[guard.OVERRIDE_ENV] = "1"
    try:
        label = "bypass env var allows a raw commit with no marker at all"
        got = run_main("git commit -m 'x'", session_id="sess-6")
        if not _testlib.report(got == 0, f"{label} (got exit={got})"):
            fails.append(label)
    finally:
        os.environ.pop(guard.OVERRIDE_ENV, None)
        if saved_bypass is not None:
            os.environ[guard.OVERRIDE_ENV] = saved_bypass

# --- prefilter re-check: a real repo, a real gate run, todo 844 ---
# A marker-authorized commit chaining the gate with `;` must still block on a
# failing gate: the hook re-runs the gate itself, not the shell's exit status.

with tempfile.TemporaryDirectory() as tmp:
    repo = Path(tmp)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    (repo / "README.md").write_text("x\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)

    # Baseline for the verbatim-move case below: HEAD already holds this exact
    # 5-line comment block under a different path. Text deliberately distinct from
    # noisy.py's below - a coincidental match would silently exempt genuine new noise too.
    (repo / "source_move.py").write_text(
        "# m1\n# m2\n# m3\n# m4\n# m5\nprint('keep')\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "source_move.py"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "add source_move"], cwd=repo, check=True)

    # An em dash trips em-dash.sh, which gates this 5-line comment block.
    # Written as an escape, never a literal: em-dash.sh's exempt marker only covers
    # .claude/todos/, so a literal one would make this file uncommittable.
    (repo / "noisy.py").write_text(
        "print('a \u2014 b')\n", encoding="utf-8"
    )
    (repo / "clean.py").write_text("print('ok')\n", encoding="utf-8")

    # Move the block out of source_move.py into moved.py, same commit's pathspec -
    # the gate must not re-flag lines already present at HEAD under another path (todo 899).
    (repo / "source_move.py").write_text("print('keep')\n", encoding="utf-8")
    (repo / "moved.py").write_text(
        "# m1\n# m2\n# m3\n# m4\n# m5\nprint('moved')\n", encoding="utf-8"
    )

    guard.MARKER_DIR = repo
    guard.SESSION_MARKER_DIR = repo / ".session-markers"
    guard.SESSION_MARKER_DIR.mkdir(parents=True)
    guard.session_marker_path("sess-gate").touch()

    label = "a `;`-chained commit is blocked when its own pathspec fails the gate"
    got = run_main(
        "bash prefilter-gate.sh noisy.py ; git commit -m 'x' -- noisy.py",
        session_id="sess-gate",
        cwd=str(repo),
    )
    if not _testlib.report(got == 2, f"{label} (got exit={got})"):
        fails.append(label)

    label = "a `;`-chained commit still lands when its own pathspec passes the gate"
    got = run_main(
        "bash prefilter-gate.sh clean.py ; git commit -m 'x' -- clean.py",
        session_id="sess-gate",
        cwd=str(repo),
    )
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)

    label = "the prescribed `&&` form still commits with no extra friction"
    got = run_main(
        "bash prefilter-gate.sh clean.py && git commit -m 'x' -- clean.py",
        session_id="sess-gate",
        cwd=str(repo),
    )
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)

    label = "a pathspec-less commit is not force-checked (fails open, decided: accepted gap, todo 868)"
    got = run_main("git commit -m 'x'", session_id="sess-gate", cwd=str(repo))
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)

    label = "a verbatim comment-block move across files in the same commit is not re-flagged"
    got = run_main(
        "git commit -m 'x' -- source_move.py moved.py",
        session_id="sess-gate",
        cwd=str(repo),
    )
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)

    label = "a verbatim move alongside a genuinely flagged file still blocks"
    got = run_main(
        "git commit -m 'x' -- source_move.py moved.py noisy.py",
        session_id="sess-gate",
        cwd=str(repo),
    )
    if not _testlib.report(got == 2, f"{label} (got exit={got})"):
        fails.append(label)

# --- todo 917: an expired legacy marker is pruned on the next commit attempt ---
# even one that itself gets denied, since pruning happens before the
# allow/deny decision, not conditional on it.

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir
    guard.SESSION_MARKER_DIR = tmpdir / ".session-markers"
    guard.SESSION_MARKER_DIR.mkdir(parents=True)

    expired_marker = tmpdir / ".commit-marker-long-dead"
    expired_marker.touch()
    old = time.time() - guard.FRESHNESS_SECONDS - 30
    os.utime(expired_marker, (old, old))

    label = "a commit attempt (even a denied one) prunes an already-expired legacy marker"
    got = run_main("git commit -m 'x'", session_id="sess-prune")
    pruned_ok = not expired_marker.exists()
    if not _testlib.report(got == 2 and pruned_ok, f"{label} (deny exit={got}, pruned={pruned_ok})"):
        fails.append(label)

# --- AI attribution: refused even from a session that holds a marker ---

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir
    guard.SESSION_MARKER_DIR = tmpdir / ".session-markers"
    guard.SESSION_MARKER_DIR.mkdir(parents=True)
    (guard.SESSION_MARKER_DIR / "sess-attr").touch()

    for label, command, expect in (
        ("a Co-Authored-By: Claude trailer is refused",
         "git commit -m 'X' -m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'", 2),
        ("a trailer inside one multi-line -m is refused",
         "git commit -m 'X\n\nco-authored-by: Someone <a@anthropic.com>'", 2),
        ("a --message= Generated with Claude Code line is refused",
         "git commit --message='X Generated with [Claude Code](https://claude.com)'", 2),
        ("a trailer in the bundled -am form is refused",
         "git commit -am 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'", 2),
        ("a trailer attached to a bundled -amVALUE is refused",
         "git commit '-amCo-Authored-By: Claude <noreply@anthropic.com>'", 2),
        ("a human Co-Authored-By is allowed",
         "git commit -m 'X' -m 'Co-Authored-By: Jane Doe <jane@example.com>'", 0),
        ("a subject that only mentions Claude in prose is allowed",
         "git commit -m 'FIX: Player Claude listener'", 0),
    ):
        got = run_main(command, session_id="sess-attr")
        if not _testlib.report(got == expect, f"{label} (got exit={got}, want {expect})"):
            fails.append(label)

    (tmpdir / "msg-ai.txt").write_text("X\n\nCo-Authored-By: Claude <noreply@anthropic.com>\n", encoding="utf-8")
    (tmpdir / "msg-ok.txt").write_text("FIX: Player Claude listener\n", encoding="utf-8")
    for label, command, expect in (
        ("a trailer read from -F <file> is refused", "git commit -F msg-ai.txt", 2),
        ("a trailer read from --file=<file> is refused", "git commit --file=msg-ai.txt", 2),
        ("a clean -F <file> is allowed", "git commit -F msg-ok.txt", 0),
        ("a missing -F file is left to git", "git commit -F nope.txt", 0),
    ):
        got = run_main(command, session_id="sess-attr", cwd=str(tmpdir))
        if not _testlib.report(got == expect, f"{label} (got exit={got}, want {expect})"):
            fails.append(label)

sys.exit(_testlib.summarize(fails, style="count"))
