"""Self-test for ui-screenshot-reminder.py (todo 326, global reminder rebuild).

Run directly: python hooks/test_ui_screenshot_reminder.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_HOOK_PATH = _HOOKS_DIR / "ui-screenshot-reminder.py"
guard = _testlib.load_module("guard", _HOOK_PATH)

# (path, expect_ui, label)
UNIT_CASES = [
    ("src/components/Button.tsx", True, "extension + segment both match"),
    ("lib/features/foo/ui/widget.dart", True, "lib/**/ui/ Flutter path"),
    ("app/screens/Home.jsx", True, "screens segment"),
    ("src/widgets/Card.vue", True, "widgets segment + .vue ext"),
    ("styles/theme.scss", True, ".scss extension alone"),
    ("server/routes/users.py", False, "backend python, no match"),
    ("README.md", False, "docs, no match"),
    (".claude\\hooks\\commit-guard.py", False, "windows-style backslash path, backend"),
    ("lib\\ui\\dialog.dart", True, "windows-style backslash path, ui segment"),
]


def check_unit(case) -> bool:
    path, expect_ui, label = case
    got = guard.is_ui_path(path)
    ok = got == expect_ui
    print(f"[{'PASS' if ok else 'FAIL'}] unit: {label}: {path!r} -> {got}")
    return ok


def run_hook(cwd: str, session_id: str) -> subprocess.CompletedProcess:
    payload = {"session_id": session_id, "cwd": cwd}
    return subprocess.run(
        [sys.executable, str(_HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def init_repo(root: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=root, check=True)
    (root / "README.md").write_text("init\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=root, check=True)


def cleanup_marker(session_id: str) -> None:
    marker = guard.session_marker_path(session_id)
    if marker.exists():
        marker.unlink()


def integration_checks() -> list[str]:
    fails: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="ui-reminder-test-"))
    try:
        repo = tmp / "repo"
        repo.mkdir()
        init_repo(repo)

        # Case 1: UI file changed -> fires once.
        session_a = f"test-{uuid.uuid4()}"
        (repo / "src").mkdir(parents=True, exist_ok=True)
        (repo / "src" / "Button.tsx").write_text("export const Button = () => null;\n", encoding="utf-8")
        try:
            proc = run_hook(str(repo), session_a)
            fired = '"decision": "block"' in proc.stdout
            ok = fired and proc.returncode == 0
            print(f"[{'PASS' if ok else 'FAIL'}] integration: UI file changed fires -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
            if not ok:
                fails.append("UI file changed fires")

            # Case 2: second call, same session -> silent.
            proc2 = run_hook(str(repo), session_a)
            silent = proc2.stdout.strip() == "" and proc2.returncode == 0
            print(f"[{'PASS' if silent else 'FAIL'}] integration: second call same session stays silent -> exit={proc2.returncode} stdout={proc2.stdout.strip()!r}")
            if not silent:
                fails.append("second call same session silent")
        finally:
            cleanup_marker(session_a)

        # Case 3: backend-only changes -> silent, new session (fresh repo,
        # so case 1's leftover untracked .tsx file can't leak into this check).
        repo_b = tmp / "repo-backend"
        repo_b.mkdir()
        init_repo(repo_b)
        session_b = f"test-{uuid.uuid4()}"
        (repo_b / "server").mkdir(parents=True, exist_ok=True)
        (repo_b / "server" / "app.py").write_text("print('hi')\n", encoding="utf-8")
        try:
            proc = run_hook(str(repo_b), session_b)
            silent = proc.stdout.strip() == "" and proc.returncode == 0
            print(f"[{'PASS' if silent else 'FAIL'}] integration: backend-only changes stay silent -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
            if not silent:
                fails.append("backend-only silent")
        finally:
            cleanup_marker(session_b)

        # Case 4: no-git-repo cwd -> does not crash, stays silent.
        non_repo = tmp / "not-a-repo"
        non_repo.mkdir()
        session_c = f"test-{uuid.uuid4()}"
        try:
            proc = run_hook(str(non_repo), session_c)
            ok = proc.returncode == 0 and proc.stdout.strip() == ""
            print(f"[{'PASS' if ok else 'FAIL'}] integration: no-git-repo does not crash -> exit={proc.returncode} stdout={proc.stdout.strip()!r} stderr={proc.stderr.strip()!r}")
            if not ok:
                fails.append("no-git-repo does not crash")
        finally:
            cleanup_marker(session_c)

        # Case 5: malformed stdin (forces an internal exception) -> exits 0.
        proc = subprocess.run(
            [sys.executable, str(_HOOK_PATH)],
            input="not valid json {{{",
            capture_output=True,
            text=True,
        )
        ok = proc.returncode == 0
        print(f"[{'PASS' if ok else 'FAIL'}] integration: thrown internal error still exits 0 -> exit={proc.returncode} stderr={proc.stderr.strip()!r}")
        if not ok:
            fails.append("thrown internal error exits 0")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return fails


def run() -> int:
    fails = _testlib.run_cases(UNIT_CASES, check_unit) + integration_checks()
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
