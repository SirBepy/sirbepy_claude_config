"""Self-test for ci/run_all.py's skill-script test discovery (todo 991).

Run directly: python tools/test_run_all.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Loads ci/run_all.py by path (its own CLI entry point has no importable
package) and drives discover_skill_tests()/check_skill_tests() against a
scratch git repo, never the real ~/.claude tree - a concurrent lane's
in-flight edits elsewhere in skills/ must not be able to change this suite's
pass/fail. Covers: a tracked sibling test_*.py beside a script is found and
actually run; an untracked one is not (mirrors run_hook_tests.py's todo-805
fix); skills/commit is excluded so its three suites are never run twice; and
a failing discovered test fails the check.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))
# run_all.py does a bare `from _cilib import tracked_files`, which only
# resolves when ci/ is on sys.path - true when it runs as `python ci/run_all.py`
# (script dir goes on sys.path[0]), not true for a by-path load like this one.
sys.path.insert(0, str(ROOT / "ci"))

import _testlib  # noqa: E402

RUN_ALL = ROOT / "ci" / "run_all.py"
run_all = _testlib.load_module("run_all", RUN_ALL)


def _git(args, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)


def _init_repo(tmp: Path) -> None:
    _git(["init", "-q"], tmp)
    _git(["config", "user.email", "test@example.com"], tmp)
    _git(["config", "user.name", "Test"], tmp)
    _git(["config", "core.autocrlf", "false"], tmp)


def _commit(tmp: Path, rel_path: str, content: str) -> None:
    full = tmp / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    _git(["add", rel_path], tmp)
    _git(["commit", "-q", "-m", "scratch"], tmp)


def check_tracked_sibling_test_is_discovered_and_run() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _init_repo(tmp)
        _commit(tmp, "skills/widget/widget.py", "x = 1\n")
        _commit(tmp, "skills/widget/test_widget.py", "import sys\nsys.exit(0)\n")
        found = run_all.discover_skill_tests(tmp)
        rels = {p.relative_to(tmp).as_posix() for p in found}
        if "skills/widget/test_widget.py" not in rels:
            print(f"not discovered: {rels}")
            return False
        ok, detail = run_all.check_skill_tests(tmp)
        if not ok:
            print(detail)
        return ok


def check_untracked_sibling_test_is_not_discovered() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _init_repo(tmp)
        _commit(tmp, "skills/widget/widget.py", "x = 1\n")
        untracked = tmp / "skills" / "widget" / "test_widget.py"
        untracked.write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
        found = run_all.discover_skill_tests(tmp)
        return found == []


def check_skills_commit_is_excluded() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _init_repo(tmp)
        _commit(tmp, "skills/commit/some_script.sh", "#!/bin/sh\ntrue\n")
        _commit(tmp, "skills/commit/test_some_script.sh", "#!/bin/sh\nexit 0\n")
        found = run_all.discover_skill_tests(tmp)
        return found == []


def check_failing_discovered_test_fails_the_check() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        _init_repo(tmp)
        _commit(tmp, "skills/widget/widget.py", "x = 1\n")
        _commit(tmp, "skills/widget/test_widget.py", "import sys\nsys.exit(1)\n")
        ok, detail = run_all.check_skill_tests(tmp)
        return (not ok) and "test_widget.py" in detail


def check_no_skills_dir_is_a_clean_empty_pass() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        return run_all.discover_skill_tests(tmp) == []


def main() -> int:
    cases = (
        ("tracked sibling test is discovered and run", check_tracked_sibling_test_is_discovered_and_run),
        ("untracked sibling test is not discovered", check_untracked_sibling_test_is_not_discovered),
        ("skills/commit is excluded (no double-run)", check_skills_commit_is_excluded),
        ("failing discovered test fails the check", check_failing_discovered_test_fails_the_check),
        ("missing skills/ dir is a clean empty pass", check_no_skills_dir_is_a_clean_empty_pass),
    )
    fails = []
    for label, fn in cases:
        ok = fn()
        print(f"{'PASS' if ok else 'FAIL'}: {label}")
        if not ok:
            fails.append(label)
    if fails:
        print(f"FAIL: {len(fails)} of {len(cases)} tests failed")
        return 1
    print(f"OK: {len(cases)}/{len(cases)} tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
