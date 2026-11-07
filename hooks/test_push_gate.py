"""Self-test for push-gate.py.

Run directly: python hooks/test_push_gate.py
End-to-end cases build throwaway git repos in a temp dir and point the marker
dir there, so the real hooks/.push-ok/ is never read or written.
"""

import os
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

    # A Git Bash `cd /c/...` drive path reaches the same repo as `cd C:/...`
    # (Windows only: elsewhere `/c/...` is a real path, not a drive alias).
    posix_client = client.as_posix()
    if os.name == "nt" and posix_client[1:3] == ":/":
        msys_client = f"/{posix_client[0].lower()}{posix_client[2:]}"
        expect("Git Bash cd /c/... into an uncleared repo is denied", call_main(f"cd {msys_client}; git push origin develop", personal), 2)
        expect("Git Bash git -C /c/... into an uncleared repo is denied", call_main(f"git -C {msys_client} push", personal), 2)
    expect("an unresolvable cd target is judged by the cwd repo (uncleared, denied)", call_main("cd /no/such/dir/anywhere; git push", client), 2)
    expect("an unresolvable cd target from a cleared cwd passes", call_main("cd /no/such/dir/anywhere; git push", personal), 0)

    # A delete-only push uploads no commits, so the code-check/e2e gate has
    # nothing to check; anything that also sends a commit stays gated. `client`
    # has an unmarked HEAD, which is the shape that was wrongly denied.
    allowed = [
        "git push origin --delete foo",
        "git push --delete origin foo",
        "git push origin :foo",
        "git push -d origin foo",
        "git push origin --delete foo bar",
        "git push origin :foo :bar",
        "git push https://x-access-token:abc@github.com/o/r.git --delete foo",
        "git push https://github.com/o/r.git :foo",
        "git push --force origin --delete foo",
        "git push --delete --repo=origin foo",
        "git push origin --delete foo 2>&1",
        f'git -C "{client}" push origin --delete foo',
        f'cd "{client}" && git push origin --delete foo',
    ]
    for cmd in allowed:
        expect(f"delete-only passes on an unmarked HEAD: {cmd}", call_main(cmd, client), 0)

    denied = [
        "git push",
        "git push origin",
        "git push origin main",
        "git push origin main :foo",
        "git push origin :foo main",
        "git push origin --delete foo main:main",
        "git push --delete origin",
        "git push --delete foo",
        "git push origin :",
        "git push --all origin :foo",
        "git push --mirror origin :foo",
        "git push --tags origin :foo",
        "git push --follow-tags origin :foo",
        "git push --force origin main :foo",
        "git push origin +main :foo",
        "git push origin +:foo",
        "git push --delete origin :foo",
        "git push origin --delete $branch",
        "git push --unknown-flag origin :foo",
        "git push origin --delete foo && git push origin main",
        "git push origin main && git push origin --delete foo",
        "git push origin --delete foo; git push",
        "git push origin --delete foo && echo $(git push origin main)",
        f'git -C "{client}" status && git push origin main',
    ]
    for cmd in denied:
        expect(f"push that sends a commit stays denied: {cmd}", call_main(cmd, client), 2)

sys.exit(_testlib.summarize(fails, style="count"))
