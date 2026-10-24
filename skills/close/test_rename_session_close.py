"""Self-test for rename-session.ps1's host-managed refusal on -Close.

Only the refusing paths are exercised. A non-refused -Close resolves the
session by walking up to the ancestor claude.exe and schedules its kill, so
running that path from a test would kill the session running the test.
"""
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "rename-session.ps1"


def run_close(entrypoint):
    env = dict(os.environ)
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


def main():
    if os.name != "nt":
        print("SKIP test_rename_session_close.py: rename-session.ps1 is the Windows script")
        return 0
    tests = [test_sdk_cli_refuses, test_any_sdk_entrypoint_refuses]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {t.__name__}: {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
