"""Self-test runner for skills/impeccable/scripts/hook-lib.test.mjs (todo 1063).

Run directly: python tools/test_impeccable_hook_lib.py
Exits 0 on all-pass, 1 on any failure.

hook-lib.mjs is pure-ish JS with no Python port, so this shells out to
`node --test` against its own test file rather than reimplementing the
dedupe/cache logic here - the point is to exercise the real module, not a
restatement of it. Node 18+ ships `--test` built in; no extra dependency.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))

import _testlib  # noqa: E402

TEST_FILE = ROOT / "skills" / "impeccable" / "scripts" / "hook-lib.test.mjs"


def run_node_test() -> bool:
    if not TEST_FILE.is_file():
        return _testlib.report(False, f"{TEST_FILE} is missing")
    result = subprocess.run(
        ["node", "--test", str(TEST_FILE)],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    output = (result.stdout or "") + (result.stderr or "")
    print(output)
    return _testlib.report(result.returncode == 0, "node --test hook-lib.test.mjs")


def main() -> int:
    fails = [] if run_node_test() else ["node --test hook-lib.test.mjs"]
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(main())
