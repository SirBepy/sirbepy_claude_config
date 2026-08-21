"""Discovers and runs every tools/test_*.py self-test, one subprocess each.

Twin of run_hook_tests.py for the scripts under tools/. Those scripts are not
hooks and never run in-session, but they carry real parsing logic, so they get
the same mechanical floor. Only offline, money-free tests belong here: the
harnesses under tools/ that spend tokens are exercised by hand, never by CI.
"""

import argparse
import subprocess
import sys
from pathlib import Path

TEST_GLOB = "test_*.py"
TIMEOUT_SECONDS = 120


def discover(root: Path) -> list:
    tools_dir = root / "tools"
    if not tools_dir.is_dir():
        return []
    return sorted(p for p in tools_dir.glob(TEST_GLOB) if "__pycache__" not in p.parts)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    root = args.root.resolve()

    tests = discover(root)
    print(f"discovered {len(tests)} tool test suite(s) under {root / 'tools'}")
    if not tests:
        print("FAIL: zero tool test suites discovered")
        return 1

    fails = []
    for test_path in tests:
        rel = test_path.relative_to(root)
        try:
            proc = subprocess.run(
                [sys.executable, str(rel)], cwd=root, capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=TIMEOUT_SECONDS,
            )
            ok = proc.returncode == 0
        except subprocess.TimeoutExpired:
            ok, proc = False, None
        print(f"{'PASS' if ok else 'FAIL'} {test_path.name}")
        if not ok:
            fails.append(test_path.name)
            if proc is None:
                print(f"--- TIMEOUT after {TIMEOUT_SECONDS}s ---")
            else:
                print(f"--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}")

    if fails:
        print(f"FAIL: {len(fails)} of {len(tests)} tool test suites failed")
        return 1
    print(f"OK: {len(tests)}/{len(tests)} tool test suites passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
