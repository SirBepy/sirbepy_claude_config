"""Self-test for client-push-gate.py and _client_repo.py.

Run directly: python hooks/test_client_push_gate.py
End-to-end cases build throwaway git repos in a temp dir and point the
client list and marker dir there, so the real refs/client-repos.txt and
hooks/.client-push-ok/ are never read or written.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
guard = _testlib.load_module("client_push_gate", _HOOKS_DIR / "client-push-gate.py")
lib = guard._client_repo

fails = []

# --- origin_slug: every remote URL shape the listed repos actually use ---

SLUG_CASES = [
    ("https://github.com/Revaire-Inc/revaire-mobile.git", "revaire-inc/revaire-mobile", "https with .git"),
    ("git@github-work:zirtue-corp/zng-admin.git", "zirtue-corp/zng-admin", "scp-style host alias"),
    ("ssh://git@github.com/zirtue-corp/zng-api", "zirtue-corp/zng-api", "ssh url, no .git"),
    ("https://github.com/SirBepy/foo/", "sirbepy/foo", "trailing slash"),
    ("", None, "empty url"),
    ("nonsense", None, "single segment"),
]


def check_slug(case) -> bool:
    url, expected, label = case
    got = lib.origin_slug(url)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(SLUG_CASES, check_slug)

# --- git_dash_c_path: Windows paths must survive tokenizing ---

DASH_C_CASES = [
    (r'git -C "C:\Users\tecno\Desktop\Projects\zng-app" push', r"C:\Users\tecno\Desktop\Projects\zng-app", "quoted backslash path"),
    ("git -C C:/repo push origin main", "C:/repo", "bare forward-slash path"),
    ("git push", None, "no -C"),
]


def check_dash_c(case) -> bool:
    command, expected, label = case
    got = guard.git_dash_c_path(command)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(DASH_C_CASES, check_dash_c)

# --- end to end against real temp repos ---


def git(repo: Path, *args) -> None:
    # Inline identity: the CI runner has no global git user configured.
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo), *args],
        check=True,
        capture_output=True,
    )


def make_repo(root: Path, name: str, origin: str) -> Path:
    repo = root / name
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "remote", "add", "origin", origin)
    (repo / "f.txt").write_text("x", encoding="utf-8")
    git(repo, "add", "f.txt")
    git(repo, "commit", "-q", "-m", "init")
    return repo


def call_main(command: str, cwd: Path) -> int:
    guard.read_payload = lambda: {"hook_event_name": "PreToolUse", "tool_name": "Bash", "tool_input": {"command": command}, "cwd": str(cwd)}
    try:
        guard.main()
        return 0
    except SystemExit as e:
        return e.code


def expect(label: str, got, expected) -> None:
    global fails
    ok = got == expected
    fails += [] if _testlib.report(ok, f"{label} (expected {expected}, got {got})") else [label]


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    client_list = tmpdir / "client-repos.txt"
    client_list.write_text("# comment line\nZirtue-Corp/ZNG-App\n", encoding="utf-8")
    lib.CLIENT_LIST_PATH = client_list
    lib.MARKER_DIR = tmpdir / ".client-push-ok"

    client = make_repo(tmpdir, "zng-app-followup", "git@github-work:zirtue-corp/zng-app.git")
    personal = make_repo(tmpdir, "mine", "https://github.com/SirBepy/mine.git")
    elsewhere = tmpdir / "not-a-repo"
    elsewhere.mkdir()

    expect("client repo push with no marker is blocked", call_main("git push", client), 2)
    expect("non-push git command in a client repo passes", call_main("git status", client), 0)
    expect("personal repo push passes", call_main("git push", personal), 0)
    expect("push outside any repo fails open", call_main("git push", elsewhere), 0)
    expect("-C into a client repo is gated even from a personal cwd", call_main(f'git -C "{client}" push', personal), 2)
    expect("mark CLI refuses a personal repo", lib.main(["mark", str(personal), "--reason", "x"]), 2)

    lib.main(["mark", str(client), "--reason", "code-check + e2e passed"])
    expect("push passes once HEAD is marked", call_main("git push", client), 0)

    (client / "f.txt").write_text("y", encoding="utf-8")
    git(client, "commit", "-q", "-am", "second")
    expect("a new commit needs a fresh mark", call_main("git push", client), 2)

    client_list.unlink()
    expect("a missing client list fails open", call_main("git push", client), 0)

sys.exit(_testlib.summarize(fails, style="count"))
