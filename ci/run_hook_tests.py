"""Discovers and runs every hooks/test_*.py self-test, one subprocess each.

These suites already share a harness (hooks/_testlib.py, todo 316); this is
only the runner that makes CI invoke them instead of relying on a prose step
in the /commit skill. Each suite is run in place (cwd = repo root, invoked as
hooks/test_x.py) so hooks/_testlib.py's by-path import via sys.path[0] keeps
working exactly as it does when a human runs `python hooks/test_x.py`.
"""

import argparse
import subprocess
import sys
from pathlib import Path

TEST_GLOB = "test_*.py"
TIMEOUT_SECONDS = 120


def discover(root: Path) -> list:
    hooks_dir = root / "hooks"
    return sorted(
        p for p in hooks_dir.glob(TEST_GLOB)
        if "__pycache__" not in p.parts
    )


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
