"""Discovers and runs every hooks/test_*.py self-test, one subprocess each.

These suites already share a harness (hooks/_testlib.py, todo 316); this is
only the runner that makes CI invoke them instead of relying on a prose step
in the /commit skill. Each suite is run in place (cwd = repo root, invoked as
hooks/test_x.py) so hooks/_testlib.py's by-path import via sys.path[0] keeps
working exactly as it does when a human runs `python hooks/test_x.py`.

Discovery skips any test_*.py that git does not track (todo 805): a peer
session's half-written untracked test file is not yet part of the committed
contract this gate protects, so it must not be able to fail this gate. If git
itself is unavailable, discovery falls back to every file on disk.
"""

import argparse
import subprocess
import sys
from pathlib import Path

TEST_GLOB = "test_*.py"
TIMEOUT_SECONDS = 120


def _tracked_hook_files(root: Path):
    """Returns the set of `hooks/*` paths git has in its index, or None if
    git could not be queried (non-repo checkout, git missing).
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "hooks"],
            capture_output=True, text=True, timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def discover(root: Path) -> list:
    hooks_dir = root / "hooks"
    candidates = sorted(
        p for p in hooks_dir.glob(TEST_GLOB)
        if "__pycache__" not in p.parts
    )
    tracked = _tracked_hook_files(root)
    if tracked is None:
        return candidates
    return [p for p in candidates if p.relative_to(root).as_posix() in tracked]


def run_one(root: Path, test_path: Path) -> tuple:
    rel = test_path.relative_to(root)
    try:
        proc = subprocess.run(
            [sys.executable, str(rel)],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return False, "", f"TIMEOUT: exceeded {TIMEOUT_SECONDS}s"
    return proc.returncode == 0, proc.stdout, proc.stderr


def main() -> int:
    parser = argparse.ArgumentParser()
    default_root = Path(__file__).resolve().parent.parent
    parser.add_argument("--root", type=Path, default=default_root)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()

    tests = discover(root)
    print(f"discovered {len(tests)} hook test suite(s) under {root / 'hooks'}")
    if not tests:
        print("FAIL: zero hook test suites discovered")
        return 1

    fails = []
    for test_path in tests:
        name = test_path.name
        ok, stdout, stderr = run_one(root, test_path)
        print(f"{'PASS' if ok else 'FAIL'} {name}")
        if not ok:
            fails.append(name)
            print(f"--- stdout ({name}) ---\n{stdout}")
            print(f"--- stderr ({name}) ---\n{stderr}")
        elif args.verbose:
            print(f"--- stdout ({name}) ---\n{stdout}")
            if stderr:
                print(f"--- stderr ({name}) ---\n{stderr}")

    total = len(tests)
    if fails:
        print(f"FAIL: {len(fails)} of {total} hook test suites failed")
        return 1
    print(f"OK: {total}/{total} hook test suites passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
