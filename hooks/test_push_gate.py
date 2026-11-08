"""Self-test for push-gate.py.

Run directly: python hooks/test_push_gate.py
End-to-end cases build throwaway git repos in a temp dir and point the marker
dir there, so the real hooks/.push-ok/ is never read or written.
"""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
guard = _testlib.load_module("push_gate", _HOOKS_DIR / "push-gate.py")

# The mark CLI reads the running session's own transcript; hide the real session id
# so every case is hermetic unless it passes --transcript.
os.environ.pop("CLAUDE_CODE_SESSION_ID", None)

fails = []

# --- git_dash_c_path: Windows paths must survive tokenizing ---

DASH_C_CASES = [
    (r'git -C "C:\Users\tecno\Desktop\Projects\zng-app" push', r"C:\Users\tecno\Desktop\Projects\zng-app", "quoted backslash path"),
    ("git -C C:/repo push origin main", "C:/repo", "bare forward-slash path"),
    ("git push", None, "no -C"),
    ("git.exe -C C:/repo push origin main", "C:/repo", "git.exe spelling still reads the push's own -C"),
    # todo 1044: a chained, unrelated `git -C` before the push must never be
    # attributed to the push itself.
    ('git -C "C:/cleared" status && git push', None, "earlier unrelated git -C is not the push's own"),
    ('git -C "C:/cleared" status && git -C "C:/target" push', "C:/target", "push's own -C survives an earlier unrelated git -C"),
    # A value-taking global flag before -C must not hide the push's own -C: push-read-gate
    # already sees such a push, so the target must resolve to the same repo.
    ("git --attr-source HEAD -C C:/other push", "C:/other", "--attr-source value does not hide -C"),
    ("git --config-env a=B -C C:/other push origin", "C:/other", "--config-env value does not hide -C"),
    ("git --super-prefix p/ -C C:/other push", "C:/other", "--super-prefix value does not hide -C"),
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

# --- mark refuses unless /test and /e2e were really loaded ---


def tool_use(tool_id: str, name: str, **tool_input) -> dict:
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}]}}


def tool_result(tool_id: str, text: str, is_error: bool = False) -> dict:
    return {"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": tool_id, "is_error": is_error, "content": [{"type": "text", "text": text}]},
    ]}}


def skill(tool_id: str, name: str) -> list:
    return [tool_use(tool_id, "Skill", skill=name), tool_result(tool_id, f"Launching skill: {name}")]


def push(tool_id: str, ok: bool) -> list:
    text = "To origin\n  a..b  main -> main" if ok else "[push-gate] HEAD abc1234 has not been cleared for push."
    return [tool_use(tool_id, "Bash", command="git push"), tool_result(tool_id, text, is_error=not ok)]


def user_prompt(text: str) -> dict:
    return {"type": "user", "message": {"content": text}}


def run_mark(repo: Path, reason: str, entries, *extra):
    """(exit code, stderr text, marker written?) of one mark call against a transcript."""
    transcript = repo.parent / f"{repo.name}-transcript.jsonl"
    transcript.write_text("\n".join(json.dumps(e) for e in entries) + "\n", encoding="utf-8")
    sha = guard.head_sha(repo)
    marker = guard.MARKER_DIR / sha
    if marker.exists():
        marker.unlink()
    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        code = guard.cli(["mark", str(repo), "--reason", reason, "--transcript", str(transcript), *extra])
    return code, err.getvalue(), marker.exists()


def make_stack_repo(root: Path, name: str, files: dict) -> Path:
    repo = make_repo(root, name, "https://github.com/SirBepy/x.git")
    for rel, text in files.items():
        (repo / rel).write_text(text, encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "stack")
    return repo


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.MARKER_DIR = tmpdir / ".push-ok"
    node = make_stack_repo(tmpdir, "node-app", {"package.json": json.dumps({"scripts": {"test": "vitest run"}})})
    flutter = make_stack_repo(tmpdir, "flutter-app", {"pubspec.yaml": "name: a\nflutter:\n  uses-material-design: true\n"})
    docs = make_repo(tmpdir, "notes-only", "https://github.com/SirBepy/notes.git")
    reason = "code-check + e2e passed"

    code, err, marked = run_mark(node, reason, [user_prompt("push it")])
    expect("a session that loaded neither skill is refused", (code, marked), (2, False))
    expect("the refusal names /test and /e2e", "/test" in err and "/e2e" in err, True)

    code, err, marked = run_mark(node, reason, [user_prompt("push it")] + skill("t1", "test"))
    expect("/test alone is refused, naming /e2e only", (code, marked, "/e2e" in err, "/test," in err), (2, False, True, False))

    both = [user_prompt("push it")] + skill("t1", "test") + skill("t2", "e2e")
    expect("both skills loaded: mark accepted", run_mark(node, reason, both)[::2], (0, True))

    typed = [user_prompt("<command-message>test</command-message>\n<command-name>/test</command-name>")] + skill("t2", "e2e")
    expect("a user-typed /test counts as loaded", run_mark(node, reason, typed)[::2], (0, True))

    plugin = [user_prompt("push it")] + skill("t1", "test") + skill("t2", "my-plugin:e2e")
    expect("a plugin-qualified e2e skill counts", run_mark(node, reason, plugin)[::2], (0, True))

    nosuite = "code-check passed, e2e: no suite"
    expect("e2e: no suite waives e2e when /test is loaded", run_mark(node, nosuite, [user_prompt("x")] + skill("t1", "test"))[::2], (0, True))
    expect("e2e: no suite does not waive /test", run_mark(node, nosuite, [user_prompt("x")])[::2], (2, False))

    old = [user_prompt("x")] + skill("t1", "test") + skill("t2", "e2e") + push("p1", True) + [user_prompt("more work")]
    expect("skills loaded before the last successful push do not count", run_mark(node, reason, old)[::2], (2, False))

    denied_then_mark = [user_prompt("x")] + skill("t1", "test") + skill("t2", "e2e") + push("p1", False)
    expect("a denied push does not erase the skills loaded for it", run_mark(node, reason, denied_then_mark)[::2], (0, True))

    # pc-review item 14: a push that sends nothing is not the boundary the skills must follow.
    def pushed_with(command: str) -> list:
        return [tool_use("p9", "Bash", command=command), tool_result("p9", "Everything up-to-date")]

    loaded = [user_prompt("x")] + skill("t1", "test") + skill("t2", "e2e")
    for dry in ("git push --dry-run", "git push -n origin main", "git push origin main --dry-run", "git push -nv origin main",
                "git -C /some/repo push --dry-run origin main", "git push --dry-run --force-with-lease origin main",
                "git push --dry-run origin main 2>&1", "git push --dry-run && git push -n"):
        expect(f"a dry-run push is not the boundary: {dry}", run_mark(node, reason, loaded + pushed_with(dry))[::2], (0, True))
    for real in ("git push", "git push origin main", "git push --dry-run && git push origin main", "git push -n; git push",
                 "git push --push-option -n origin main", "git push -o -n origin main"):
        expect(f"a real push still is the boundary: {real}", run_mark(node, reason, loaded + pushed_with(real))[::2], (2, False))

    after_push = old + skill("t3", "test") + skill("t4", "e2e")
    expect("skills loaded again after the push count", run_mark(node, reason, after_push)[::2], (0, True))

    no_flutter = [user_prompt("x")] + skill("t1", "test") + skill("t2", "e2e")
    code, err, marked = run_mark(flutter, reason, no_flutter)
    expect("a Flutter repo also needs /flutter-e2e", (code, marked, "/flutter-e2e" in err), (2, False, True))
    scripted = make_stack_repo(tmpdir, "flutter-scripted", {"pubspec.yaml": "name: b\nflutter:\n  uses-material-design: true\n"})
    (scripted / "e2e").mkdir()
    (scripted / "e2e" / "run-all.js").write_text("// suite", encoding="utf-8")
    git(scripted, "add", ".")
    git(scripted, "commit", "-q", "-m", "e2e suite")
    expect("a Flutter repo with e2e/run-all.js runs it via /e2e and needs no /flutter-e2e", run_mark(scripted, reason, no_flutter)[::2], (0, True))
    expect("a Flutter repo with /flutter-e2e loaded is accepted", run_mark(flutter, reason, no_flutter + skill("t3", "flutter-e2e"))[::2], (0, True))

    expect("a repo with no fast-check stack needs no skills", run_mark(docs, "notes repo: no code", [user_prompt("x")])[::2], (0, True))

    gate_prompt = "Run /commit's Push pipeline from step 2 (skip step 1c). Read snippets/auto-commit.md. /close"
    expect("a gate chat is not asked for /test", run_mark(node, reason, [user_prompt(gate_prompt)] + skill("t2", "e2e"))[::2], (0, True))
    expect("a gate chat still needs /e2e", run_mark(node, reason, [user_prompt(gate_prompt)])[::2], (2, False))

    code, err, marked = run_mark(node, "pushing past a red e2e", [user_prompt("x")], "--skip-skill-check", "Joe said yes to pushing past the red e2e")
    expect("--skip-skill-check with his approval marks", (code, marked), (0, True))
    expect("the marker records the skipped check", "skill check skipped" in (guard.MARKER_DIR / guard.head_sha(node)).read_text(encoding="utf-8"), True)
    expect("--skip-skill-check with a blank reason is refused", run_mark(node, reason, [user_prompt("x")], "--skip-skill-check", " ")[::2], (2, False))

    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        code = guard.cli(["mark", str(node), "--reason", reason, "--transcript", str(tmpdir / "missing.jsonl")])
    expect("an unreadable transcript warns and still marks", (code, "not verified" in err.getvalue()), (0, True))

    (guard.MARKER_DIR / guard.head_sha(node)).unlink(missing_ok=True)
    os.environ["CLAUDE_CODE_SESSION_ID"] = "00000000-no-such-session"
    err = io.StringIO()
    with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
        code = guard.cli(["mark", str(node), "--reason", reason])
    os.environ.pop("CLAUDE_CODE_SESSION_ID", None)
    expect("no transcript for the session id warns and still marks", (code, "not verified" in err.getvalue()), (0, True))


sys.exit(_testlib.summarize(fails, style="count"))
