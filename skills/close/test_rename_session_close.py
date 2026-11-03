"""Self-test for the host-managed refusal on close, in rename-session.ps1 (-Close) and
rename-session.sh (--close).

The .ps1 tests exercise only the refusing paths: a non-refused -Close resolves the session by
walking up to the ancestor claude.exe and schedules its kill, so running that path from a test
would kill the session running the test. The .sh tests point the script at a fake session record
whose pid is a throwaway sleeper process, so even its kill path only touches that sleeper.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "rename-session.ps1"


def run_close(entrypoint):
    # The script exits early when %USERPROFILE%\.claude\sessions is missing, as it is on a bare
    # CI runner, so give it an empty one of its own instead of depending on this machine's.
    with tempfile.TemporaryDirectory() as home:
        (Path(home) / ".claude" / "sessions").mkdir(parents=True)
        env = dict(os.environ)
        env["USERPROFILE"] = home
        env["CLAUDE_CODE_ENTRYPOINT"] = entrypoint
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-File", str(SCRIPT), "-Close"],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
    return proc.returncode, proc.stdout + proc.stderr


def test_sdk_cli_refuses():
    code, out = run_close("sdk-cli")
    assert code == 3, f"expected exit 3, got {code}: {out}"
    assert "REFUSED: host-managed session" in out, out
    assert "close_session" in out, out
    assert "Scheduled kill" not in out, out


def test_any_sdk_entrypoint_refuses():
    code, out = run_close("sdk-ts")
    assert code == 3, f"expected exit 3, got {code}: {out}"
    assert "Scheduled kill" not in out, out


SH_SCRIPT = Path(__file__).resolve().parent / "rename-session.sh"
SKIP = "skip"


def run_close_sh(entrypoint, *extra_args):
    """Run rename-session.sh --close under a throwaway HOME holding one fake session record.

    The script resolves its session through `python3`, which on Windows is often the Microsoft
    Store stub, so a shim on PATH points it at this interpreter. Returns None (skip) when no
    usable bash sees the temp HOME (a WSL bash does not inherit it).
    """
    bash = shutil.which("bash")
    if not bash:
        return None
    sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp) / "home"
            sessions = home / ".claude" / "sessions"
            sessions.mkdir(parents=True)
            (sessions / "fake.json").write_text(
                json.dumps({"pid": sleeper.pid, "sessionId": "test-sid", "procStart": "t0"}), encoding="utf-8")
            bin_dir = Path(tmp) / "bin"
            bin_dir.mkdir()
            shim = bin_dir / "python3"
            shim.write_text(f'#!/bin/sh\nexec "{Path(sys.executable).as_posix()}" "$@"\n', encoding="utf-8", newline="\n")
            shim.chmod(0o755)
            env = dict(os.environ)
            env.update(HOME=str(home), USERPROFILE=str(home), CLAUDE_CODE_SESSION_ID="test-sid",
                       CLAUDE_CODE_ENTRYPOINT=entrypoint, PATH=str(bin_dir) + os.pathsep + env.get("PATH", ""))
            probe = subprocess.run([bash, "-c", 'test -d "$HOME/.claude/sessions" && python3 -c "print(1)"'],
                                   env=env, capture_output=True, text=True, timeout=60)
            if probe.returncode != 0 or probe.stdout.strip() != "1":
                return None
            proc = subprocess.run([bash, str(SH_SCRIPT), "--close", *extra_args], env=env,
                                  capture_output=True, text=True, timeout=60)
            return proc.returncode, proc.stdout + proc.stderr
    finally:
        sleeper.kill()
        sleeper.wait()


def test_sh_sdk_entrypoint_refuses_close():
    res = run_close_sh("sdk-cli")
    if res is None:
        return SKIP
    code, out = res
    assert code == 3, f"expected exit 3, got {code}: {out}"
    assert "REFUSED: host-managed session" in out, out
    assert "close_session" in out, out
    assert "Scheduled kill" not in out, out


def test_sh_force_overrides_the_refusal():
    res = run_close_sh("sdk-cli", "--force")
    if res is None:
        return SKIP
    code, out = res
    assert code == 0, f"expected exit 0, got {code}: {out}"
    assert "REFUSED" not in out, out
    assert "Scheduled kill" in out, out


def main():
    tests = []
    if os.name == "nt":
        tests += [test_sdk_cli_refuses, test_any_sdk_entrypoint_refuses]
    else:
        print("SKIP the rename-session.ps1 tests: it is the Windows script")
    tests += [test_sh_sdk_entrypoint_refuses_close, test_sh_force_overrides_the_refusal]
    failed = 0
    for t in tests:
        try:
            if t() == SKIP:
                print(f"SKIP {t.__name__}: no bash that sees a temp HOME")
                continue
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
