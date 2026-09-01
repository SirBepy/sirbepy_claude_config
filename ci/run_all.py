"""Single entry point for every mechanical check in this repo.

Run as `python ci/run_all.py`. Each check is a sibling script with the same
contract: `--root <path>`, exit 0 pass, non-zero fail. Adding a check here is
what makes it gate anything, both in `.github/workflows/ci.yml` and in
`/commit`'s step 6a.
"""

import argparse
import importlib.util
import subprocess
import sys
from pathlib import Path

CHECKS = (
    ("hook self-tests", "run_hook_tests.py"),
    ("tool self-tests", "run_tool_tests.py"),
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


def check_hook_imports(root: Path) -> bool:
    """Exec-loads every `_hooklib` importer among hooks/*.py directly, so a
    broken symbol fails HERE, not when dev-backend-guard.py's broad
    `^(Bash|PowerShell)$` matcher fail-closes every shell call (todo 850).
    """
    print("\n=== hook import smoke (check_hook_imports) ===", flush=True)
    hooks_dir = root / "hooks"
    importers = [
        p for p in sorted(hooks_dir.glob("*.py"))
        if not p.stem.startswith(("test_", "_"))
        and "_hooklib" in p.read_text(encoding="utf-8")
    ]
    failed = []
    for path in importers:
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except BaseException as e:
            failed.append(path.name)
            print(f"FAIL: {path.name} raised on import: {e!r}")
    if failed:
        print(f"FAIL: {len(failed)} of {len(importers)} _hooklib importer(s) failed to import")
        return False
    print(f"OK: all {len(importers)} _hooklib importers import cleanly")
    return True


def main() -> int:
    ci_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ci_dir.parent)
    args = parser.parse_args()
    root = args.root.resolve()

    print(f"repo root: {root}")
    failed = [label for label, name in CHECKS if not run_check(label, ci_dir / name, root)]
    total = len(CHECKS) + 1
    if not check_hook_imports(root):
        failed.append("hook import smoke")

    print("\n" + "=" * 48)
    if failed:
        print(f"FAIL: {len(failed)} of {total} checks failed: {', '.join(failed)}")
        return 1
    print(f"OK: all {total} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
