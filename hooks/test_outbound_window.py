"""Self-test for _outbound_window.py and its two callers (pc-1217).

Run directly: python hooks/test_outbound_window.py
Builds throwaway git repos with a client and a personal origin, pins the commit-window clock
and points its allow dir at a temp dir, so the real hooks/.commit-window-ok/ is never touched.
"""

import contextlib
import io
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import _testlib
import _outbound_window

_HOOKS_DIR = Path(__file__).resolve().parent
verify_guard = _testlib.load_module("verify_guard", _HOOKS_DIR / "outbound-verify-guard.py")
create_guard = _testlib.load_module("create_guard", _HOOKS_DIR / "shortcut-create-guard.py")
cw = _outbound_window.commit_window()

SC = "https://api.app.shortcut.com/api/v3/stories"
SESSION = "sess-w"
fails = []


def expect(label: str, ok: bool, detail="") -> None:
    global fails
    fails += [] if _testlib.report(ok, f"{label} {detail}") else [label]


def at(hh: int, mm: int = 0) -> datetime:
    return datetime(2026, 11, 7, hh, mm)


def git(repo: Path, *args) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo), *args],
        check=True, capture_output=True,
    )


def make_repo(root: Path, name: str, origin: str) -> Path:
    repo = root / name
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "remote", "add", "origin", origin)
    return repo


def run_main(guard, payload: dict) -> tuple:
    """(exit code, stderr) of the guard's main() for `payload`."""
    guard.read_payload = lambda: payload
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        try:
            guard.main()
            code = 0
        except SystemExit as e:
            code = e.code
    return code, err.getvalue()


def bash(command: str, cwd: Path, session: str = SESSION) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd), "session_id": session}


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    cw.ALLOW_DIR = tmpdir / ".commit-window-ok"
    client = make_repo(tmpdir, "zng-app-wt", "git@github-work:zirtue-corp/zng-app.git")
    personal = make_repo(tmpdir, "mine", "https://github.com/SirBepy/mine.git")

    def pin(now: datetime) -> None:
        cw.now_fn = lambda: now

    # --- the shared helper ---
    pin(at(2, 0))
    msg = _outbound_window.window_denial(bash("x", client), "Shortcut REST write")
    expect("client repo at 02:00 is denied", bool(msg))
    expect("the denial names the window", bool(msg) and "23:00-10:59" in msg)
    expect("the denial names the override", bool(msg) and "--scope outbound" in msg and "commit-window-guard.py allow" in msg)
    expect("the denial names the 11:00 wake-up", bool(msg) and "2026-11-07T11:00" in msg)
    expect("personal repo at 02:00 passes", _outbound_window.window_denial(bash("x", personal), "x") is None)
    expect("a cwd outside any repo passes", _outbound_window.window_denial(bash("x", tmpdir), "x") is None)
    expect("no cwd passes", _outbound_window.window_denial({"session_id": SESSION}, "x") is None)
    pin(at(23, 0))
    expect("client repo at 23:00 is denied", bool(_outbound_window.window_denial(bash("x", client), "x")))
    pin(at(22, 59))
    expect("client repo at 22:59 passes", _outbound_window.window_denial(bash("x", client), "x") is None)
    pin(at(10, 59))
    expect("client repo at 10:59 is denied", bool(_outbound_window.window_denial(bash("x", client), "x")))
    pin(at(11, 5))
    expect("client repo at 11:05 passes", _outbound_window.window_denial(bash("x", client), "x") is None)

    # --- a broken commit-window-guard.py (it exit(0)s on a failed import) must not end the caller ---
    saved = _outbound_window._commit_window
    _outbound_window._commit_window = None
    real_spec = _outbound_window.importlib.util.spec_from_file_location

    def exiting_loader(*a, **k):
        raise SystemExit(0)

    _outbound_window.importlib.util.spec_from_file_location = exiting_loader
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            result = _outbound_window.window_denial(bash("x", client), "x")
    finally:
        _outbound_window.importlib.util.spec_from_file_location = real_spec
        _outbound_window._commit_window = saved
    expect("a SystemExit while loading the commit window fails open instead of ending the hook", result is None)

    # --- the approval is its own scope ---
    pin(at(2, 0))
    cw.grant(SESSION, str(client), "Joe: yes commit", at(2, 0))
    expect("a commit-window allow does not clear ticket posting", bool(_outbound_window.window_denial(bash("x", client), "x")))
    code = cw.cli(["allow", str(client), "--scope", "outbound", "--reason", "Joe: yes post it", "--session", SESSION])
    expect("allow --scope outbound succeeds", code == 0)
    expect("the outbound allow clears the same session", _outbound_window.window_denial(bash("x", client), "x") is None)
    expect("the outbound allow is per session", bool(_outbound_window.window_denial(bash("x", client, "sess-other"), "x")))
    expect("an outbound allow does not clear a commit", not cw.is_allowed(SESSION + "-x", str(client), at(2, 0)) and cw.is_allowed(SESSION, str(client), at(2, 0), scope="outbound"))
    pin(at(11, 0))
    expect("the allow never outlives the window", bool(not cw.is_allowed(SESSION, str(client), at(11, 0), scope="outbound")))

    # --- both callers ---
    comment = f"gh pr comment 12 --body \"{'The biller address field skips validation when the country is empty.'}\""
    create = f"curl -s -X POST {SC} -H 'Shortcut-Token: t' -d @payload.json"
    for sess, label in (("sess-v1", "outbound-verify-guard"),):
        pin(at(2, 0))
        code, err = run_main(verify_guard, bash(comment, client, sess))
        expect(f"{label}: PR comment from a client repo at 02:00 is denied by the window", code == 2 and "[outbound-window]" in err, err[:80])
        code, err = run_main(verify_guard, bash(comment, personal, sess))
        expect(f"{label}: the same comment from a personal repo is not window-denied", "[outbound-window]" not in err)
        code, err = run_main(verify_guard, bash("gh pr view 12", client, sess))
        expect(f"{label}: a read from a client repo at 02:00 passes", code == 0)
        code, err = run_main(verify_guard, bash(f"curl -s {SC}/12", client, sess))
        expect(f"{label}: a GET from a client repo at 02:00 passes", code == 0)
        pin(at(11, 5))
        code, err = run_main(verify_guard, bash(comment, client, sess))
        expect(f"{label}: at 11:05 the window is not what denies it", "[outbound-window]" not in err)

    pin(at(2, 0))
    code, err = run_main(create_guard, bash(create, client, "sess-c1"))
    expect("shortcut-create-guard: a create from a client repo at 02:00 is denied by the window", code == 2 and "[outbound-window]" in err, err[:80])
    code, err = run_main(create_guard, bash(create, personal, "sess-c1"))
    expect("shortcut-create-guard: personal repo create falls through to the ground check", code == 2 and "ground-check" in err and "[outbound-window]" not in err)
    pin(at(11, 5))
    code, err = run_main(create_guard, bash(create, client, "sess-c1"))
    expect("shortcut-create-guard: at 11:05 the window is not what denies it", "[outbound-window]" not in err)
    pin(at(2, 0))
    cw.cli(["allow", str(client), "--scope", "outbound", "--reason", "Joe: yes", "--session", "sess-c1"])
    code, err = run_main(create_guard, bash(create, client, "sess-c1"))
    expect("shortcut-create-guard: with Joe's allow the window steps aside", "[outbound-window]" not in err)

sys.exit(_testlib.summarize(fails, style="count"))
