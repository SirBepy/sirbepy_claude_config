"""Self-test for push-gate.py.

Run directly: python hooks/test_push_gate.py
End-to-end cases build throwaway git repos in a temp dir and point the marker
dir there, so the real hooks/.push-ok/ is never read or written.
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
guard = _testlib.load_module("push_gate", _HOOKS_DIR / "push-gate.py")

fails = []

# --- git_dash_c_path: Windows paths must survive tokenizing ---

DASH_C_CASES = [
    (r'git -C "C:\Users\tecno\Desktop\Projects\zng-app" push', r"C:\Users\tecno\Desktop\Projects\zng-app", "quoted backslash path"),
    ("git -C C:/repo push origin main", "C:/repo", "bare forward-slash path"),
    ("git push", None, "no -C"),
    # todo 1044: a chained, unrelated `git -C` before the push must never be
    # attributed to the push itself.
    ('git -C "C:/cleared" status && git push', None, "earlier unrelated git -C is not the push's own"),
    ('git -C "C:/cleared" status && git -C "C:/target" push', "C:/target", "push's own -C survives an earlier unrelated git -C"),
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
    # Per-repo content: identical trees committed in the same second share a sha, and so a marker.
    (repo / "f.txt").write_text(name, encoding="utf-8")
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
    guard.MARKER_DIR = tmpdir / ".push-ok"

    client = make_repo(tmpdir, "zng-app-followup", "git@github-work:zirtue-corp/zng-app.git")
    personal = make_repo(tmpdir, "mine", "https://github.com/SirBepy/mine.git")
    elsewhere = tmpdir / "not-a-repo"
    elsewhere.mkdir()

    expect("client repo push with no marker is blocked", call_main("git push", client), 2)
    expect("personal repo push with no marker is blocked", call_main("git push", personal), 2)
    expect("non-push git command passes", call_main("git status", personal), 0)
    expect("push outside any repo fails open", call_main("git push", elsewhere), 0)
    expect("mark CLI accepts a personal repo", guard.cli(["mark", str(personal), "--reason", "code-check passed, e2e: no suite"]), 0)
    expect("personal push passes once HEAD is marked", call_main("git push", personal), 0)
    expect("a marked repo does not clear another repo's HEAD", call_main("git push", client), 2)
    expect("-C into an unmarked repo is gated from a marked repo's cwd", call_main(f'git -C "{client}" push', personal), 2)

    (personal / "f.txt").write_text("y", encoding="utf-8")
    git(personal, "commit", "-q", "-am", "second")
    expect("a new commit needs a fresh mark", call_main("git push", personal), 2)

    # todo 1044: resolve the repo the push actually runs in, not the first
    # `-C` in the command or the payload cwd regardless of a `cd`/`-C` ahead
    # of it. `personal`'s current HEAD (the second commit above) is cleared
    # here so it can stand in as the "cleared" side of each case; `client`'s
    # HEAD has never been marked, so it stands in as "uncleared".
    guard.cli(["mark", str(personal), "--reason", "code-check passed, e2e: no suite"])

    expect(
        "cd into an uncleared repo from a cleared cwd is denied",
        call_main(f'cd "{client}" && git push', personal),
        2,
    )
    expect(
        "an earlier git -C into a cleared repo does not clear a push from an uncleared cwd",
        call_main(f'git -C "{personal}" status && git push', client),
        2,
    )
    expect(
        "an earlier git -C into an uncleared repo does not block a push from a cleared cwd",
        call_main(f'git -C "{client}" status && git push', personal),
        0,
    )

sys.exit(_testlib.summarize(fails, style="count"))
