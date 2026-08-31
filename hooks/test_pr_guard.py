"""Self-test for pr-guard.py.

Run directly: python hooks/test_pr_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Covers gh_pr_action/cd_target's token-aware parsing, then drives the real
guard.main() with a monkeypatched read_payload against a temp MARKER_DIR -
no live gh, no subprocess, no network. pr_is_owned's own `gh pr view` call
is proven unreachable by monkeypatching `guard.shutil.which` to return None
(the function's own first early-return), and main()'s "edit, owned" path is
covered by monkeypatching guard.pr_is_owned itself rather than letting a
real one run. Deny-path assertions check only the exit code (2), never the
reworded bypass message (todo 463).
"""

import os
import sys
import tempfile
import types
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "pr-guard.py"
)

# --- gh_pr_action: token-aware, mutating action + target extraction ---

ACTION_CASES = [
    ("gh pr create --title x", ("create", None), "create with a flag right after, no target"),
    ("gh pr edit 123 --title y", ("edit", "123"), "edit with a numeric target"),
    ("gh pr view 123", ("view", "123"), "view is parsed too, just not mutating"),
    ("gh --repo owner/name pr create", ("create", None), "global --repo flag skipped"),
    ('echo "gh pr create"', None, "gh pr create only inside one quoted token"),
    ("gh issue create", None, "gh issue, not gh pr"),
    ("gh pr comment 123 -b hi", ("comment", "123"), "comment is parsed, code-review's own path"),
]


def check_action(case) -> bool:
    command, expected, label = case
    got = guard.gh_pr_action(command)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails = _testlib.run_cases(ACTION_CASES, check_action)

# --- cd_target ---

CD_CASES = [
    ("cd /some/path && gh pr create", "/some/path", "leading cd is picked up"),
    ("gh pr create", None, "no cd at all"),
]


def check_cd(case) -> bool:
    command, expected, label = case
    got = guard.cd_target(command)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(CD_CASES, check_cd)

# --- pr_is_owned: proven to never reach a real subprocess ---

guard.shutil = types.SimpleNamespace(which=lambda name: None)
label = "pr_is_owned returns False with no gh binary found, no subprocess reached"
got = guard.pr_is_owned("123", "C:/repo", "gh pr edit 123")
if not _testlib.report(got is False, label):
    fails.append(label)

# --- main() end to end, temp marker dir only ---


def run_main(command: str) -> int:
    guard.read_payload = lambda: {"tool_input": {"command": command}, "cwd": "C:/repo"}
    try:
        guard.main()
        return 0
    except SystemExit as e:
        return e.code


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir

    label = "gh pr view is read-only, never gated"
    got = run_main("gh pr view 123")
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)

    label = "gh pr comment is /code-review's own path, never gated here"
    got = run_main("gh pr comment 123 -b hi")
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)

    label = "gh pr create with no marker and no ownership stub is blocked"
    guard.pr_is_owned = lambda target, cwd, command: False
    got = run_main("gh pr create --title x")
    if not _testlib.report(got == 2, f"{label} (got exit={got})"):
        fails.append(label)

    marker = tmpdir / ".pr-marker-abc"
    marker.touch()
    label = "a fresh .pr-marker is consumed and allows create"
    got = run_main("gh pr create --title x")
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)
    label = "the marker is deleted after being consumed"
    if not _testlib.report(not marker.exists(), label):
        fails.append(label)
    label = "the next create with the marker gone is blocked again"
    got = run_main("gh pr create --title x")
    if not _testlib.report(got == 2, f"{label} (got exit={got})"):
        fails.append(label)

    label = "edit is allowed with no marker when pr_is_owned (stubbed) says True"
    guard.pr_is_owned = lambda target, cwd, command: True
    got = run_main("gh pr edit 123 --title y")
    if not _testlib.report(got == 0, f"{label} (got exit={got})"):
        fails.append(label)

    label = "edit is blocked with no marker when pr_is_owned (stubbed) says False"
    guard.pr_is_owned = lambda target, cwd, command: False
    got = run_main("gh pr edit 123 --title y")
    if not _testlib.report(got == 2, f"{label} (got exit={got})"):
        fails.append(label)

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir
    guard.pr_is_owned = lambda target, cwd, command: False

    saved_bypass = os.environ.pop(guard.OVERRIDE_ENV, None)
    os.environ[guard.OVERRIDE_ENV] = "1"
    try:
        label = "bypass env var allows a raw create with no marker at all"
        got = run_main("gh pr create --title x")
        if not _testlib.report(got == 0, f"{label} (got exit={got})"):
            fails.append(label)
    finally:
        os.environ.pop(guard.OVERRIDE_ENV, None)
        if saved_bypass is not None:
            os.environ[guard.OVERRIDE_ENV] = saved_bypass

sys.exit(_testlib.summarize(fails, style="count"))
