"""Single entry point for every mechanical check in this repo.

Run as `python ci/run_all.py`. Each check is a sibling script with the same
contract: `--root <path>`, exit 0 pass, non-zero fail. Adding a check here is
what makes it gate anything, both in `.github/workflows/ci.yml` and in
`/commit`'s step 6a.
"""

import argparse
import subprocess
import sys
from pathlib import Path

CHECKS = (
    ("hook self-tests", "run_hook_tests.py"),
    ("skill frontmatter", "check_skill_frontmatter.py"),
    ("instruction budget", "check_instruction_budget.py"),
)


def run_check(label: str, script: Path, root: Path) -> bool:
    print(f"\n=== {label} ({script.name}) ===", flush=True)
    if not script.is_file():
        print(f"FAIL: {script} is missing")
        return False
    result = subprocess.run(
        [sys.executable, str(script), "--root", str(root)],
        cwd=str(root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=600,
    )
    for stream in (result.stdout, result.stderr):
        if stream:
            print(stream.rstrip(), flush=True)
    if result.returncode != 0:
        print(f"FAIL: {label} exited {result.returncode}")
        return False
    return True


def main() -> int:
    ci_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ci_dir.parent)
    args = parser.parse_args()
    root = args.root.resolve()

    print(f"repo root: {root}")
    failed = [label for label, name in CHECKS if not run_check(label, ci_dir / name, root)]

    print("\n" + "=" * 48)
    if failed:
        print(f"FAIL: {len(failed)} of {len(CHECKS)} checks failed: {', '.join(failed)}")
        return 1
    print(f"OK: all {len(CHECKS)} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
