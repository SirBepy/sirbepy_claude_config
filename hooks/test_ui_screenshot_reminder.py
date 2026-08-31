"""Self-test for ui-screenshot-reminder.py (todo 326, global reminder rebuild;
todo 821, mtime-compare predicate replacing the once-per-session marker).

Run directly: python hooks/test_ui_screenshot_reminder.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
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
    ("lib/app_header.dart", True, ".dart extension alone, no ui segment"),
    ("server/routes/users.py", False, "backend python, no match"),
    ("README.md", False, "docs, no match"),
    (".claude\\hooks\\commit-guard.py", False, "windows-style backslash path, backend"),
    ("lib\\ui\\dialog.dart", True, "windows-style backslash path, ui segment"),
]


def touch(path: Path, at: float) -> None:
    """Create (or update) `path` and pin its mtime to `at`, so ordering
    between UI edits and screenshots is deterministic instead of relying on
    real-time sleeps and filesystem clock granularity.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("x", encoding="utf-8")
    os.utime(path, (at, at))


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


def integration_checks() -> list[str]:
    fails: list[str] = []
    tmp = Path(tempfile.mkdtemp(prefix="ui-reminder-test-"))
    try:
        repo = tmp / "repo"
        repo.mkdir()
        init_repo(repo)

        # Case 1: UI file changed, zero screenshots anywhere -> fires
        # (existing zero-screenshot behaviour, must not regress).
        session_a = f"test-{uuid.uuid4()}"
        touch(repo / "src" / "Button.tsx", time.time())
        proc = run_hook(str(repo), session_a)
        fired = '"decision": "block"' in proc.stdout
        ok = fired and proc.returncode == 0
        print(f"[{'PASS' if ok else 'FAIL'}] integration: zero screenshots, UI edit fires -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not ok:
            fails.append("zero screenshots fires")

        # Case 2: UI edit, then a screenshot postdating it, then a SECOND UI
        # edit postdating the screenshot -> must fire (todo 821's core gap).
        repo_c = tmp / "repo-refire"
        repo_c.mkdir()
        init_repo(repo_c)
        session_c = f"test-{uuid.uuid4()}"
        t0 = time.time()
        ui_file = repo_c / "lib" / "ui" / "widget.dart"
        touch(ui_file, t0)
        touch(repo_c / ".for_bepy" / "screenshots" / "sess-1" / "shot.png", t0 + 100)
        # Sanity: screenshot already postdates the only edit -> quiet here.
        pre = run_hook(str(repo_c), session_c)
        pre_ok = pre.stdout.strip() == "" and pre.returncode == 0
        print(f"[{'PASS' if pre_ok else 'FAIL'}] integration: refire setup, screenshot postdates edit stays quiet -> exit={pre.returncode} stdout={pre.stdout.strip()!r}")
        if not pre_ok:
            fails.append("refire setup quiet before second edit")
        touch(ui_file, t0 + 200)
        proc = run_hook(str(repo_c), session_c)
        fired = '"decision": "block"' in proc.stdout
        ok = fired and proc.returncode == 0
        print(f"[{'PASS' if ok else 'FAIL'}] integration: second UI edit after screenshot fires -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not ok:
            fails.append("second UI edit after screenshot fires")

        # Case 3: UI edit, then a screenshot postdating it, no further edit
        # -> stays quiet.
        repo_d = tmp / "repo-covered"
        repo_d.mkdir()
        init_repo(repo_d)
        session_d = f"test-{uuid.uuid4()}"
        t0 = time.time()
        touch(repo_d / "lib" / "ui" / "widget.dart", t0)
        touch(repo_d / ".for_bepy" / "screenshots" / "sess-1" / "shot.png", t0 + 100)
        proc = run_hook(str(repo_d), session_d)
        silent = proc.stdout.strip() == "" and proc.returncode == 0
        print(f"[{'PASS' if silent else 'FAIL'}] integration: screenshot covers last edit, no further edit stays quiet -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not silent:
            fails.append("screenshot covers edit stays quiet")

        # Case 4: backend-only changes -> silent, new session (fresh repo,
        # so case 1's leftover untracked .tsx file can't leak into this check).
        repo_b = tmp / "repo-backend"
        repo_b.mkdir()
        init_repo(repo_b)
        session_b = f"test-{uuid.uuid4()}"
        touch(repo_b / "server" / "app.py", time.time())
        proc = run_hook(str(repo_b), session_b)
        silent = proc.stdout.strip() == "" and proc.returncode == 0
        print(f"[{'PASS' if silent else 'FAIL'}] integration: backend-only changes stay silent -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not silent:
            fails.append("backend-only silent")

        # Case 5: no-git-repo cwd -> does not crash, stays silent.
        non_repo = tmp / "not-a-repo"
        non_repo.mkdir()
        session_e = f"test-{uuid.uuid4()}"
        proc = run_hook(str(non_repo), session_e)
        ok = proc.returncode == 0 and proc.stdout.strip() == ""
        print(f"[{'PASS' if ok else 'FAIL'}] integration: no-git-repo does not crash -> exit={proc.returncode} stdout={proc.stdout.strip()!r} stderr={proc.stderr.strip()!r}")
        if not ok:
            fails.append("no-git-repo does not crash")

        # Case 6: malformed stdin (forces an internal exception) -> exits 0.
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
