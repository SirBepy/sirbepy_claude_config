"""Self-test for gh-account-switch.sh (todo 1069).

Run directly: python hooks/test_gh_account_switch.py
Drives the real script via bash, in a real throwaway git repo (so
`git remote get-url origin` behaves exactly as it does for the live hook),
with a stub `gh` prepended onto PATH that logs every invocation instead of
touching the real gh CLI or its real logged-in accounts.
"""

import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
SCRIPT = _HOOKS_DIR / "gh-account-switch.sh"
TIMEOUT_SECONDS = 30

fails = []


def _bash_exe() -> str:
    """A bash that can actually run this script - bare `bash` on a Windows
    GitHub runner resolves to WSL with no distro installed (see
    ci/run_all.py's own _bash_exe, duplicated here rather than imported
    since hooks/ tests do not depend on ci/)."""
    if os.name != "nt":
        return "bash"
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        r"C:\Program Files\Git\usr\bin\bash.exe",
    ):
        if Path(candidate).is_file():
            return candidate
    found = shutil.which("bash")
    if found and "system32" not in found.lower():
        return found
    return "bash"


BASH = _bash_exe()

STUB_GH = """#!/bin/bash
echo "$@" >> "$STUB_GH_LOG"
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
    printf 'github.com\\n  \xe2\x9c\x93 Logged in to github.com account %s (keyring)\\n  - Active account: true\\n' "$STUB_GH_ACTIVE_ACCOUNT"
    exit 0
fi
exit 0
"""


def make_stub_bin(tmpdir: Path) -> Path:
    bin_dir = tmpdir / "stub-bin"
    bin_dir.mkdir()
    gh_path = bin_dir / "gh"
    gh_path.write_text(STUB_GH, encoding="utf-8", newline="\n")
    gh_path.chmod(gh_path.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return bin_dir


def run_hook(repo: Path, command: str, active_account: str, stub_bin: Path, log_path: Path) -> subprocess.CompletedProcess:
    payload = json.dumps({"tool_input": {"command": command}})
    env = os.environ.copy()
    env["PATH"] = str(stub_bin) + os.pathsep + env.get("PATH", "")
    env["STUB_GH_LOG"] = str(log_path)
    env["STUB_GH_ACTIVE_ACCOUNT"] = active_account
    return subprocess.run(
        [BASH, SCRIPT.as_posix()],
        input=payload,
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        timeout=TIMEOUT_SECONDS,
    )


def init_repo(tmpdir: Path, name: str, origin: str | None) -> Path:
    repo = tmpdir / name
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True, capture_output=True)
    if origin:
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", origin], check=True, capture_output=True)
    return repo


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    stub_bin = make_stub_bin(tmpdir)

    # --- Regression: existing origin-based switching is unchanged ---

    client_repo = init_repo(tmpdir, "client", "git@github-work:zirtue-corp/zng-app.git")
    log = tmpdir / "log-origin-switch.txt"
    proc = run_hook(client_repo, "gh pr create --fill", "SirBepy", stub_bin, log)
    label = "origin-based: zirtue-corp origin switches away from a mismatched active account"
    ok = proc.returncode == 0 and log.exists() and "auth switch --user JosipMuzicZirtue" in log.read_text(encoding="utf-8")
    fails += [] if _testlib.report(ok, f"{label} (stderr={proc.stderr!r}, log={log.read_text(encoding='utf-8') if log.exists() else None!r})") else [label]

    log2 = tmpdir / "log-origin-noop.txt"
    proc = run_hook(client_repo, "gh pr create --fill", "JosipMuzicZirtue", stub_bin, log2)
    label = "origin-based: already-matching active account makes no switch call"
    ok = proc.returncode == 0 and (not log2.exists() or "auth switch" not in log2.read_text(encoding="utf-8"))
    fails += [] if _testlib.report(ok, label) else [label]

    # --- todo 1069: gh repo create with no origin at all ---

    fresh_repo = init_repo(tmpdir, "fresh", None)

    log3 = tmpdir / "log-no-origin-create.txt"
    proc = run_hook(fresh_repo, 'gh repo create mc-plugins --private --source . --push', "JosipMuzicZirtue", stub_bin, log3)
    label = "no origin, repo create with no owner prefix: resolves to the personal account"
    ok = proc.returncode == 0 and log3.exists() and "auth switch --user SirBepy" in log3.read_text(encoding="utf-8")
    fails += [] if _testlib.report(ok, f"{label} (log={log3.read_text(encoding='utf-8') if log3.exists() else None!r})") else [label]

    log4 = tmpdir / "log-no-origin-create-mapped-owner.txt"
    proc = run_hook(fresh_repo, 'gh repo create zirtue-corp/some-tool --private', "SirBepy", stub_bin, log4)
    label = "no origin, repo create naming a mapped org owner: resolves to that org's account"
    ok = proc.returncode == 0 and log4.exists() and "auth switch --user JosipMuzicZirtue" in log4.read_text(encoding="utf-8")
    fails += [] if _testlib.report(ok, f"{label} (log={log4.read_text(encoding='utf-8') if log4.exists() else None!r})") else [label]

    log5 = tmpdir / "log-no-origin-create-noop.txt"
    proc = run_hook(fresh_repo, 'gh repo create mine --private', "SirBepy", stub_bin, log5)
    label = "no origin, repo create resolving to the already-active personal account: no switch call"
    ok = proc.returncode == 0 and (not log5.exists() or "auth switch" not in log5.read_text(encoding="utf-8"))
    fails += [] if _testlib.report(ok, label) else [label]

    # --- No origin AND not `gh repo create`: nothing to infer, leave it alone ---

    log6 = tmpdir / "log-no-origin-other.txt"
    proc = run_hook(fresh_repo, "gh pr list", "JosipMuzicZirtue", stub_bin, log6)
    label = "no origin, non-create gh command: no account decision attempted at all"
    ok = proc.returncode == 0 and not log6.exists()
    fails += [] if _testlib.report(ok, f"{label} (log exists={log6.exists()})") else [label]

    # --- A command with no 'gh' token never touches gh at all ---

    log7 = tmpdir / "log-no-gh.txt"
    proc = run_hook(fresh_repo, "git status", "SirBepy", stub_bin, log7)
    label = "command with no gh token: script exits before any gh call"
    ok = proc.returncode == 0 and not log7.exists()
    fails += [] if _testlib.report(ok, label) else [label]

sys.exit(_testlib.summarize(fails, style="count"))
