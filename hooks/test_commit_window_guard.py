"""Self-test for commit-window-guard.py.

Run directly: python hooks/test_commit_window_guard.py
End-to-end cases build throwaway git repos in a temp dir, pin the guard's
clock, and point its allow dir there, so the real hooks/.commit-window-ok/
is never read or written.
"""

import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
guard = _testlib.load_module("commit_window_guard", _HOOKS_DIR / "commit-window-guard.py")

fails = []


def expect(label: str, got, expected) -> None:
    global fails
    ok = got == expected
    fails += [] if _testlib.report(ok, f"{label} (expected {expected}, got {got})") else [label]


def at(hh: int, mm: int = 0, day: int = 6) -> datetime:
    return datetime(2026, 10, day, hh, mm, 0)


# --- detection: which invocations land a commit or push ---

DETECT_CASES = [
    ("git commit -m x -- a.txt", ["commit"], "plain git commit"),
    ('git -C "C:\\work\\zng-app" commit -m x -- a', ["commit"], "git -C with a quoted backslash path"),
    ('& git -C "C:\\work\\zng-app" push origin main', ["push"], "PowerShell call-operator push"),
    ("git.exe push", ["push"], "git.exe"),
    ('bash ~/.claude/skills/commit/commit-pathspec.sh --expect-branch m --expect-sha a -m "x" -- f', ["commit-pathspec"], "commit-pathspec.sh"),
    ("python skills/commit/split-hunks.py --repo C:/r commit -m x --whole a", ["split-hunks"], "split-hunks.py commit"),
    ("python skills/commit/split-hunks.py stage a --match x", [], "split-hunks.py stage does not land"),
    ('bash -c "git push origin main"', ["push"], "push inside bash -c"),
    ("git cherry-pick abc123", ["cherry-pick"], "cherry-pick"),
    ("git rebase --abort", [], "rebase --abort never lands"),
    ("git merge --quit", [], "merge --quit never lands"),
    ("git status", [], "status is read-only"),
    ("git log --oneline -5", [], "log is read-only"),
    ("git diff HEAD -- a.txt", [], "diff is read-only"),
    ("git commit-graph write", [], "commit-graph is not commit"),
    ('echo "remember to git push later"', [], "quoted prose mentioning git push"),
    ('gh pr create --body "then git commit and git push"', [], "PR body mentioning git commit"),
    ('git -c core.editor="git commit -m x" status', [], "git's own -c key=value is not a nested shell command"),
    ('git -C "C:/work/zng-app" -c core.editor="git commit -m x" status', [], "git -c after -C still is not a landing"),
]


def check_detect(case) -> bool:
    command, expected, label = case
    got = [kind for kind, _path, _args in guard.landing_targets(command, "C:/somewhere")]
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(DETECT_CASES, check_detect)

expect(
    "git -C path is the target, not the cwd",
    [p for _k, p, _a in guard.landing_targets('git -C "C:/target" push', "C:/cwd")],
    ["C:/target"],
)
expect(
    "cd earlier in the command pins the cwd",
    [p for _k, p, _a in guard.landing_targets('cd "C:/target" && git commit -m x', "C:/cwd")],
    ["C:/target"],
)
expect(
    "commit-pathspec.sh -C is its target",
    [p for _k, p, _a in guard.landing_targets("bash commit-pathspec.sh -C C:/target -m x -- f", "C:/cwd")],
    ["C:/target"],
)

# --- window arithmetic ---

expect("22:59 is outside", guard.in_window(at(22, 59)), False)
expect("23:00 is inside", guard.in_window(at(23, 0)), True)
expect("00:40 is inside", guard.in_window(at(0, 40)), True)
expect("10:59 is inside", guard.in_window(at(10, 59)), True)
expect("11:00 is outside", guard.in_window(at(11, 0)), False)
expect("window opened at 23:30 ends next day 11:00", guard.window_end(at(23, 30)), at(11, 0, day=7))
expect("window at 00:40 ends same day 11:00", guard.window_end(at(0, 40)), at(11, 0))

expect("ISO override hour", guard.override_hour("2026-10-06T01:15:00+02:00"), 1)
expect("git-style override hour", guard.override_hour("2026-10-06 14:30:00"), 14)
expect("RFC2822 override hour", guard.override_hour("Mon, 6 Oct 2026 23:05:10 +0200"), 23)
expect("relative override has no hour", guard.override_hour("yesterday"), None)

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
    return repo


SESSION = "sess-a"


def call_main(command: str, cwd: Path, now: datetime, session: str = SESSION) -> int:
    guard.now_fn = lambda: now
    guard.read_payload = lambda: {
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "cwd": str(cwd),
        "session_id": session,
    }
    try:
        guard.main()
        return 0
    except SystemExit as e:
        return e.code


def allow(repo: Path, now: datetime, session: str = SESSION) -> int:
    guard.now_fn = lambda: now
    return guard.cli(["allow", str(repo), "--reason", "Joe: yes push it", "--session", session])


with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    guard.ALLOW_DIR = tmpdir / ".commit-window-ok"

    client = make_repo(tmpdir, "zng-app-wt", "git@github-work:zirtue-corp/zng-app.git")
    client2 = make_repo(tmpdir, "revaire", "https://github.com/Revaire-Inc/revaire-mobile.git")
    personal = make_repo(tmpdir, "mine", "https://github.com/SirBepy/mine.git")
    night, day = at(0, 40), at(14, 0)

    expect("client commit at 00:40 is denied", call_main("git commit -m x -- f.txt", client, night), 2)
    expect("client push at 00:40 is denied", call_main("git push", client, night), 2)
    expect("client commit at 23:00 is denied", call_main("git commit -m x", client, at(23, 0)), 2)
    expect("client commit at 22:59 passes", call_main("git commit -m x", client, at(22, 59)), 0)
    expect("client commit at 11:00 passes", call_main("git commit -m x", client, at(11, 0)), 0)
    expect("client commit at 14:00 passes", call_main("git commit -m x", client, day), 0)
    expect("personal commit at 00:40 passes", call_main("git commit -m x", personal, night), 0)
    expect("personal push at 00:40 passes", call_main("git push", personal, night), 0)
    expect("client status at 00:40 passes", call_main("git status", client, night), 0)
    expect("client log at 00:40 passes", call_main("git log --oneline -3", client, night), 0)
    expect("client diff at 00:40 passes", call_main("git diff HEAD", client, night), 0)
    expect("git -C into a client repo from a personal cwd is denied", call_main(f'git -C "{client}" commit -m x', personal, night), 2)
    expect("git -C into a personal repo from a client cwd passes", call_main(f'git -C "{personal}" push', client, night), 0)
    expect("PowerShell-style push into a client repo is denied", call_main(f'& git -C "{client}" push origin main', personal, night), 2)
    expect(
        "commit-pathspec.sh into a client repo is denied",
        call_main(f'bash "C:/Users/tecno/.claude/skills/commit/commit-pathspec.sh" -C "{client}" --expect-branch main --expect-sha abc -m "x" -- f.txt', personal, night),
        2,
    )
    expect("second listed client org is gated too", call_main("git push", client2, night), 2)
    expect("client rebase --abort at 00:40 passes", call_main("git rebase --abort", client, night), 0)

    expect("allow CLI on a client repo succeeds", allow(client, at(0, 30)), 0)
    expect("allowed client commit at 00:40 passes", call_main("git commit -m x", client, night), 0)
    expect("allowed client push at 00:40 passes", call_main("git push", client, night), 0)
    expect("allow does not cover another session", call_main("git push", client, night, session="sess-b"), 2)
    expect("allow does not cover another client repo", call_main("git push", client2, night), 2)
    expect("allow expires after two hours", call_main("git push", client, at(2, 31)), 2)

    allow(client, at(10, 0))
    expect("allow granted at 10:00 still holds at 10:59", call_main("git push", client, at(10, 59)), 0)
    expect("allow never outlives the window it was granted in", call_main("git push", client, at(23, 30)), 2)

    expect("allow CLI on a personal repo writes nothing", allow(personal, night), 0)
    expect("personal allow left no marker", guard.allow_path(SESSION, guard.git_repo_root(str(personal))).exists(), False)

    expect(
        "allow chained with the commit is still denied",
        call_main(f'python C:/Users/tecno/.claude/hooks/commit-window-guard.py allow "{client2}" --reason "y" && git push', client2, night),
        2,
    )

    # Timestamps stay real.
    expect("--date into the window is denied in daytime", call_main('git commit --date="2026-10-06T01:00:00" -m x', client, day), 2)
    expect("GIT_COMMITTER_DATE into the window is denied", call_main('GIT_COMMITTER_DATE="2026-10-06 03:10:00" git commit -m x', client, day), 2)
    expect("PowerShell $env:GIT_AUTHOR_DATE into the window is denied", call_main('$env:GIT_AUTHOR_DATE = "2026-10-06 00:40:00"; git commit -m x', client, day), 2)
    expect("relative --date is denied", call_main("git commit --date=yesterday -m x", client, day), 2)
    expect("daytime --date in a client repo passes", call_main('git commit --date "2026-10-06 14:30:12" -m x', client, day), 0)
    expect("daytime --date=\"...\" with a space inside passes", call_main('git commit --date="2026-10-06 14:30:12" -m x', client, day), 0)
    expect("--date=\"...\" with a space inside into the window is denied", call_main('git commit --date="2026-10-06 02:30:12" -m x', client, day), 2)
    expect("--date on a push is not a timestamp override", call_main('git push origin main', client, day), 0)
    expect("--date into the window in a personal repo passes", call_main('git commit --date="2026-10-06T01:00:00" -m x', personal, day), 0)
    expect("any --date inside the window is denied even with an allow", call_main('git commit --date="2026-10-06 14:00:00" -m x', client, at(0, 50)), 2)

    # --date is scoped to its own chained segment: one repo's
    # override never gets checked against a different repo's own commit.
    expect(
        "a client repo in the SAME segment as an in-window --date is still denied",
        call_main(f'git -C "{personal}" commit --date="2026-10-06 02:30:00" -m x && git -C "{client}" commit --date="2026-10-06 02:30:00" -m y', personal, day),
        2,
    )
    expect(
        "a different repo's --date in an earlier chained segment does not deny this one",
        call_main(f'git -C "{personal}" commit --date="2026-10-06 02:30:00" -m x && git -C "{client}" commit -m y', personal, day),
        0,
    )
    expect(
        "a single client-repo commit with its own in-window --date is still denied",
        call_main('git commit --date="2026-10-06 02:30:00" -m y', client, day),
        2,
    )
    allow(client, at(14, 0))
    expect(
        "allowed fold replay of a real night timestamp passes in daytime",
        call_main('GIT_AUTHOR_DATE="2026-10-05T00:40:12+02:00" GIT_COMMITTER_DATE="2026-10-05T00:40:12+02:00" git commit --date="2026-10-05T00:40:12+02:00" -m x -- f', client, at(14, 5)),
        0,
    )

sys.exit(_testlib.summarize(fails, style="count"))
