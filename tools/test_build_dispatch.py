"""Self-test for skills/mega-todos/build-dispatch.ps1's generalized composer.

Run directly: python tools/test_build_dispatch.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Todo 1028: the composer was mega-todos-only (mandatory -CommitMessage and
-ExpectedBranch, hardcoded read of skills/mega-todos/SKILL.md's commit block).
This drives the real script via powershell.exe and asserts the three literal
markers hooks/dispatch-preamble-guard.py checks survive BOTH shapes:

1. -NoCommitBlock (the new generic path any orchestrator can use, no commit
   message/branch needed).
2. The existing mega-todos per-builder/barrier paths, unchanged, so the
   generalization did not regress the one caller that already depends on it.

Never imports dispatch-preamble-guard.py directly - the markers are pure
literal substrings (see that hook's own STAGING_A/STAGING_B/SCREENSHOT_MARKER
constants), duplicating them here as plain strings is the actual contract a
composed prompt has to satisfy.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "mega-todos" / "build-dispatch.ps1"
TIMEOUT_SECONDS = 60

STAGING_A = "Stage your changes but do NOT commit"
STAGING_B = "Leave all changes unstaged"
SCREENSHOT_MARKER = ".for_bepy/screenshots/"

fails = []


def run_script(*extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT), *extra],
        capture_output=True, text=True, timeout=TIMEOUT_SECONDS,
    )


def assert_markers_present(stdout: str, label: str) -> bool:
    missing = []
    if STAGING_A not in stdout and STAGING_B not in stdout:
        missing.append("staging line")
    if "run_in_background" not in stdout or "FORBIDDEN" not in stdout:
        missing.append("run_in_background/FORBIDDEN")
    if SCREENSHOT_MARKER not in stdout and "READ-ONLY DISPATCH" not in stdout:
        missing.append("screenshot-id marker")
    ok = not missing
    print(f"{'PASS' if ok else 'FAIL'}: {label}" + ("" if ok else f" (missing: {', '.join(missing)})"))
    if not ok:
        fails.append(label)
    return ok


def check(cond: bool, label: str) -> None:
    print(f"{'PASS' if cond else 'FAIL'}: {label}")
    if not cond:
        fails.append(label)


def main() -> int:
    # Case 1: -NoCommitBlock, no -CommitMessage/-ExpectedBranch at all - the
    # shape /loop-todos or /auto-do-todos would use. Must succeed and must
    # carry all three guard markers from the preamble alone.
    r1 = run_script(
        "-Owned", "foo/bar.ts",
        "-OffLimits", "everything else in the repo",
        "-Task", "do the thing",
        "-NoCommitBlock",
        "-Compact",
    )
    check(r1.returncode == 0, f"NoCommitBlock+Compact exits 0 (stderr: {r1.stderr[:300]})")
    assert_markers_present(r1.stdout, "NoCommitBlock+Compact carries all three guard markers")
    check(
        "COMMITTING IS PART OF YOUR JOB" not in r1.stdout,
        "NoCommitBlock+Compact never injects mega-todos' own commit procedure",
    )
    check(STAGING_A in r1.stdout, "NoCommitBlock+Compact defaults to the stage-don't-commit variant")

    # Case 2: -NoCommitBlock -SharedIndex selects the other documented
    # <STAGING_LINE> variant from refs/builder-preamble.md's own table.
    r2 = run_script(
        "-Owned", "foo/bar.ts",
        "-OffLimits", "everything else in the repo",
        "-Task", "do the thing",
        "-NoCommitBlock",
        "-SharedIndex",
        "-Compact",
    )
    check(r2.returncode == 0, f"NoCommitBlock+SharedIndex exits 0 (stderr: {r2.stderr[:300]})")
    check(STAGING_B in r2.stdout, "NoCommitBlock+SharedIndex selects the leave-unstaged variant")

    # Case 3: -NoCommitBlock in the full (non-Compact) shape too.
    r3 = run_script(
        "-Owned", "foo/bar.ts",
        "-OffLimits", "everything else in the repo",
        "-Task", "do the thing",
        "-NoCommitBlock",
    )
    check(r3.returncode == 0, f"NoCommitBlock full shape exits 0 (stderr: {r3.stderr[:300]})")
    assert_markers_present(r3.stdout, "NoCommitBlock full shape carries all three guard markers")
    check(
        "COMMITTING IS PART OF YOUR JOB" not in r3.stdout,
        "NoCommitBlock full shape never injects mega-todos' own commit procedure",
    )

    # Case 4: mega-todos' existing per-builder caller shape is unchanged -
    # still requires CommitMessage/ExpectedBranch, still gets the commit
    # section, still carries all three markers.
    r4 = run_script(
        "-Owned", "foo/bar.ts",
        "-OffLimits", "everything else in the repo",
        "-Task", "do the thing",
        "-CommitMessage", "FIX: something",
        "-ExpectedBranch", "master",
        "-Compact",
    )
    check(r4.returncode == 0, f"per-builder (unchanged) exits 0 (stderr: {r4.stderr[:300]})")
    assert_markers_present(r4.stdout, "per-builder (unchanged) carries all three guard markers")
    check(
        "COMMITTING IS PART OF YOUR JOB" in r4.stdout,
        "per-builder (unchanged) still injects mega-todos' own commit procedure",
    )

    # Case 5: omitting -CommitMessage/-ExpectedBranch without -NoCommitBlock
    # is a clear error, not a silent gap - the validation this adds.
    r5 = run_script(
        "-Owned", "foo/bar.ts",
        "-OffLimits", "everything else in the repo",
        "-Task", "do the thing",
    )
    check(
        r5.returncode != 0,
        "omitting -CommitMessage/-ExpectedBranch without -NoCommitBlock is rejected",
    )

    print()
    if fails:
        print(f"FAIL: {len(fails)} case(s) failed: {fails}")
        return 1
    print("OK: all build-dispatch.ps1 cases passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
