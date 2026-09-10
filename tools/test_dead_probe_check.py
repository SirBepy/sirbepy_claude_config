"""Self-test for dead-probe-check.py.

Run directly: python tools/test_dead_probe_check.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Drives the real CLI via subprocess (not an import), same as test_patch_file.py,
since dead-probe-check.py is a standalone tool invoked exactly this way. The
script shells out to `git diff` / `git grep` itself, so each check builds a
throwaway git repo (init + one commit + one uncommitted edit) rather than
feeding it a bare diff string, and runs the script with --against HEAD (its
own default) against that repo's working-tree change.

Covers the four arms from todo 977: a removed colon-bearing title/aria-label
literal is a finding; an exact id=/data-testid=/name= match is a finding; a
literal that was only ADDED (never removed) is silent; and the load-bearing
negative from todo 968's own measurement - a removed title/aria-label literal
with NO colon stays silent even when the exact word still lives in a probe
file, because the colon requirement is what separates this heuristic from the
9-false-positive version it replaced.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "hooks"))

import _testlib  # noqa: E402

SCRIPT = ROOT / "tools" / "dead-probe-check.py"


def git(args, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )


def init_repo(tmp: Path) -> None:
    git(["init", "-q"], tmp)
    git(["config", "user.email", "test@example.com"], tmp)
    git(["config", "user.name", "Test"], tmp)
    git(["config", "core.autocrlf", "false"], tmp)


def write(tmp: Path, rel_path: str, content: str) -> None:
    path = tmp / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8"))


def commit_all(tmp: Path, message: str) -> None:
    git(["add", "-A"], tmp)
    git(["commit", "-q", "-m", message], tmp)


def run_check_script(tmp: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(tmp)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def check_removed_colon_literal_is_finding() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        init_repo(tmp)
        write(tmp, "src/App.tsx", (
            "export function App() {\n"
            "  return (\n"
            '    <button title="Projects: switch view">Click</button>\n'
            "  );\n"
            "}\n"
        ))
        write(tmp, "tests/probe.spec.ts", (
            "test('switches projects', () => {\n"
            '  page.locator(\'button[title^="Projects:"]\').click();\n'
            "});\n"
        ))
        commit_all(tmp, "init")
        write(tmp, "src/App.tsx", (
            "export function App() {\n"
            "  return (\n"
            "    <button>Click</button>\n"
            "  );\n"
            "}\n"
        ))
        result = run_check_script(tmp)
        ok = (
            result.returncode == 0
            and "removed selector(s) still referenced by a probe" in result.stdout
            and "Projects:" in result.stdout
            and "probe.spec.ts" in result.stdout
        )
        return _testlib.report(ok, "removed colon literal still referenced by a probe is a finding")


def check_exact_id_match_is_finding() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        init_repo(tmp)
        write(tmp, "src/Widget.tsx", (
            "export function Widget() {\n"
            '  return <div id="widget-root">content</div>;\n'
            "}\n"
        ))
        write(tmp, "tests/widget.spec.ts", (
            "test('widget renders', () => {\n"
            '  cy.get(\'[id="widget-root"]\').should(\'exist\');\n'
            "});\n"
        ))
        commit_all(tmp, "init")
        write(tmp, "src/Widget.tsx", (
            "export function Widget() {\n"
            "  return <div>content</div>;\n"
            "}\n"
        ))
        result = run_check_script(tmp)
        ok = (
            result.returncode == 0
            and "removed selector(s) still referenced by a probe" in result.stdout
            and "widget-root" in result.stdout
            and "widget.spec.ts" in result.stdout
        )
        return _testlib.report(ok, "exact id= match still referenced by a probe is a finding")


def check_added_not_removed_is_silent() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        init_repo(tmp)
        # Probe already references the literal this diff is about to ADD, so
        # if the tool ever started scanning added lines (not just removed
        # ones) this would wrongly fire - pinning the removed-only rule.
        write(tmp, "src/App2.tsx", (
            "export function App2() {\n"
            "  return <button>Click</button>;\n"
            "}\n"
        ))
        write(tmp, "tests/probe2.spec.ts", (
            "test('switches projects', () => {\n"
            '  page.locator(\'button[title^="Projects:"]\').click();\n'
            "});\n"
        ))
        commit_all(tmp, "init")
        write(tmp, "src/App2.tsx", (
            "export function App2() {\n"
            '  return <button title="Projects: switch view">Click</button>;\n'
            "}\n"
        ))
        result = run_check_script(tmp)
        ok = (
            result.returncode == 0
            and "no orphaned selector literals found" in result.stdout
            and "removed selector" not in result.stdout
        )
        return _testlib.report(ok, "literal only added, never removed, produces no finding")


def check_removed_no_colon_is_silent() -> bool:
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        init_repo(tmp)
        write(tmp, "src/Toolbar.tsx", (
            "export function Toolbar() {\n"
            '  return <button title="Zoom">+</button>;\n'
            "}\n"
        ))
        # Probe still contains the bare word "Zoom" - proves the silence
        # below is the colon requirement at work, not just a missing hit.
        write(tmp, "tests/toolbar.spec.ts", (
            "// Zoom button legacy test reference\n"
        ))
        commit_all(tmp, "init")
        write(tmp, "src/Toolbar.tsx", (
            "export function Toolbar() {\n"
            "  return <button>+</button>;\n"
            "}\n"
        ))
        result = run_check_script(tmp)
        ok = (
            result.returncode == 0
            and "no orphaned selector literals found" in result.stdout
            and "removed selector" not in result.stdout
        )
        return _testlib.report(ok, "removed title/aria-label literal WITHOUT a colon stays silent")


def main() -> int:
    checks = [
        check_removed_colon_literal_is_finding,
        check_exact_id_match_is_finding,
        check_added_not_removed_is_silent,
        check_removed_no_colon_is_silent,
    ]
    fails = [c.__name__ for c in checks if not c()]
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(main())
