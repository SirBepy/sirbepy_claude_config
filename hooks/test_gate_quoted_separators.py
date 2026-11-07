"""Self-test: the gate guards split a shell command on separators OUTSIDE quotes only.

Run directly: python hooks/test_gate_quoted_separators.py

Covers _hooklib.split_gate_segments and the six guards that use it
(agent-shared-tree-guard, commit-window-guard, dev-backend-guard,
git-workdir-guard, push-gate, push-read-gate). Each guard gets a case where a
`;` sits inside a quoted string and must NOT read as a statement boundary, and
a case where the same text is unquoted and MUST still split (these are
fail-closed gates, so the negative proves a real chained command is still seen).
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_HOOKS_DIR))

import _hooklib  # noqa: E402

fails = []


def expect(label: str, got, expected) -> None:
    global fails
    ok = got == expected
    fails += [] if _testlib.report(ok, f"{label} (expected {expected!r}, got {got!r})") else [label]


def run_hook(script: str, payload: dict, env_extra: dict | None = None) -> int:
    env = {**os.environ, **(env_extra or {})}
    proc = subprocess.run(
        [sys.executable, str(_HOOKS_DIR / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )
    return proc.returncode


# --- _hooklib.split_gate_segments ---

SPLIT = _hooklib.split_gate_segments
expect("quoted pipe in a grep pattern stays one segment", SPLIT('grep -E "a|b|c" file'), ['grep -E "a|b|c" file'])
expect("quoted semicolon in a commit message stays one segment", SPLIT('git commit -m "x; y" -- f'), ['git commit -m "x; y" -- f'])
expect("single-quoted separator stays one segment", SPLIT("echo 'a && b'"), ["echo 'a && b'"])
expect("unquoted separators still split", SPLIT("a && b; c | d || e\nf"), ["a ", " b", " c ", " d ", " e", "f"])
expect("a lone ampersand is not a separator (2>&1)", SPLIT("make 2>&1 | tail"), ["make 2>&1 ", " tail"])
expect("separator after a closed quote splits", SPLIT('echo "a;b"; git push'), ['echo "a;b"', " git push"])
# An unterminated quote means the scan desynced (escaped quote, apostrophe in a
# heredoc body), so it falls back to the plain split instead of hiding `git push`.
expect("unbalanced quote falls back to the plain split", SPLIT("echo it's; git push"), ["echo it's", " git push"])
expect("heredoc body is kept for the gate to see", SPLIT("bash <<EOF\ngit push\nEOF"), ["bash <<EOF", "git push", "EOF"])
expect("empty command", SPLIT(""), [])
# A backslash before a quote is text to bash and a quote opener to PowerShell, so both readings' segments are returned.
expect(
    "escaped quotes do not hide a statement from the bash reading",
    "git stash pop" in [s.strip() for s in SPLIT('echo \\"; git stash pop; echo \\"')],
    True,
)
expect("an escaped quote inside a quoted span still yields the whole span", 'echo "a\\"; b"' in SPLIT('echo "a\\"; b"'), True)
expect(
    "a Windows path ending in a backslash does not hide the next statement",
    "git push" in [s.strip() for s in SPLIT('echo "C:\\dir\\"; git push')],
    True,
)

DEEP = _hooklib.split_gate_segments_deep


def deep_has(command: str, statement: str) -> bool:
    return statement in [s.strip() for s in DEEP(command)]


expect("deep: a bash -c body is split into statements", deep_has('bash -c "echo a; git stash pop"', "git stash pop"), True)
expect("deep: sh -ec body", deep_has("sh -ec 'echo a; git stash pop'", "git stash pop"), True)
expect("deep: pwsh -Command body", deep_has('pwsh -NoProfile -Command "echo a; git stash pop"', "git stash pop"), True)
expect("deep: eval body", deep_has('eval "echo a; git stash pop"', "git stash pop"), True)
expect("deep: a double-quoted command substitution", deep_has('echo "$(git stash pop)"', "git stash pop"), True)
expect("deep: a backtick substitution", deep_has("x=`git stash pop`", "git stash pop"), True)
expect("deep: a nested wrapper", deep_has("bash -c \"sh -c 'echo a; git stash pop'\"", "git stash pop"), True)
expect("deep: a single-quoted substitution is text", deep_has("echo '$(git stash pop)'", "git stash pop"), False)
expect("deep: a quoted semicolon outside any wrapper stays text", deep_has('echo "a; git stash pop"', "git stash pop"), False)
expect("deep: git -c is not a wrapper flag", deep_has('git -c "a; git stash pop" status', "git stash pop"), False)

# The Shortcut create guards strip display-only statements; an ambiguous split strips nothing.
AMBIGUOUS = 'echo \\"; curl -X POST http://x/stories -d "$B"; echo \\"'
expect("ambiguous quoting strips no display statement", _hooklib.without_display_segments(AMBIGUOUS), AMBIGUOUS)
expect(
    "unambiguous display statements are still stripped",
    "curl" in _hooklib.without_display_segments('echo "curl -X POST http://x/stories -d y"'),
    False,
)

# --- agent-shared-tree-guard ---

AGENT = {"agent_id": "aaaeae68dcacc2c9d", "agent_type": "general-purpose", "tool_name": "Bash"}
expect(
    "agent-shared-tree-guard: git stash named inside a quoted commit message is allowed",
    run_hook("agent-shared-tree-guard.py", {**AGENT, "tool_input": {"command": 'git commit -m "wip; git stash pop; done" -- f'}}),
    0,
)
expect(
    "agent-shared-tree-guard: a real chained git stash is still refused",
    run_hook("agent-shared-tree-guard.py", {**AGENT, "tool_input": {"command": 'git commit -m "x" -- f; git stash pop'}}),
    2,
)

for label, cmd in (
    ("a git stash inside a bash -c body", 'bash -c "echo a; git stash pop"'),
    ("a git stash between two escaped quotes", 'echo \\"; git stash pop; echo \\"'),
    ("a git stash inside a double-quoted substitution", 'echo "$(git stash pop)"'),
    ("a git stash inside an eval body", "eval 'echo a; git reset --hard'"),
):
    expect(f"agent-shared-tree-guard: {label} is refused", run_hook("agent-shared-tree-guard.py", {**AGENT, "tool_input": {"command": cmd}}), 2)
for label, cmd in (
    ("a stash after a clustered -ce flag", 'bash -ce "echo a; git stash pop"'),
    ("a stash in an eval after then", 'if true; then eval "git stash pop"; fi'),
    ("a stash nested five substitutions deep", "echo $(echo $(echo $(echo $(echo $(git stash pop)))))"),
    ("a stash after a paren inside quotes in a substitution", 'echo "$(echo ")" ; git stash pop)"'),
    ("a stash after a long clustered -euxc flag", "bash -euxc 'git stash pop'"),
    ("a substitution in a quoted heredoc fed to bash", "bash <<'EOF'\nx=$(git stash pop)\nEOF"),
    ("a substitution in a quoted heredoc piped to sh", "cat <<'EOF' | sh\necho $(git stash pop)\nEOF"),
):
    expect(f"agent-shared-tree-guard: {label} is refused", run_hook("agent-shared-tree-guard.py", {**AGENT, "tool_input": {"command": cmd}}), 2)
for label, cmd in (
    ("an escaped-backtick code span", 'git commit -m "never run \\`git stash pop\\` here" -- f'),
    ("a code span in a quoted heredoc commit message", "git commit -F - <<'EOF'\nBlocks `git stash` now\nEOF"),
    ("a code span in a quoted heredoc inside a substitution", "git commit -m \"$(cat <<'EOF'\nBlocks `git stash` now\nEOF\n)\""),
):
    expect(f"agent-shared-tree-guard: {label} is allowed", run_hook("agent-shared-tree-guard.py", {**AGENT, "tool_input": {"command": cmd}}), 0)
expect(
    "agent-shared-tree-guard: a stash named in a single-quoted bash -c argument of echo is allowed",
    run_hook("agent-shared-tree-guard.py", {**AGENT, "tool_input": {"command": "echo 'bash -c \"git stash pop\"'"}}),
    0,
)

# --- commit-window-guard (detection) ---

cw = _testlib.load_module("commit_window_guard_q", _HOOKS_DIR / "commit-window-guard.py")


def landing_kinds(command: str) -> list:
    return [kind for kind, _path, _args in cw.landing_targets(command, "C:/somewhere")]


expect("commit-window-guard: a push named inside a quoted --grep is not a landing", landing_kinds('git log --grep="x; git push; y"'), [])
expect("commit-window-guard: a real chained push is still a landing", landing_kinds('git log --grep="x"; git push'), ["push"])
expect(
    "commit-window-guard: a cd named inside a quoted string does not repin the cwd",
    [p for _k, p, _a in cw.landing_targets('echo "a; cd C:/other; b" && git commit -m x', "C:/cwd")],
    ["C:/cwd"],
)

# --- dev-backend-guard ---

DEV_CMD_QUOTED = 'echo "note; fvm flutter run -d chrome --dart-define-from-file=.env.dev; end"'
expect(
    "dev-backend-guard: a flutter run named inside a quoted echo is not a run",
    run_hook("dev-backend-guard.py", {"tool_name": "Bash", "tool_input": {"command": DEV_CMD_QUOTED}}),
    0,
)
expect(
    "dev-backend-guard: the same run chained for real is still blocked",
    run_hook("dev-backend-guard.py", {"tool_name": "Bash", "tool_input": {"command": "echo hi; fvm flutter run -d chrome --dart-define-from-file=.env.dev"}}),
    2,
)

DEV_RUN = "fvm flutter run -d chrome --dart-define-from-file=.env.dev"
for label, cmd in (
    ("a run inside a bash -c body", f'bash -c "echo hi; {DEV_RUN}"'),
    ("a run between two escaped quotes", f'echo \\"; {DEV_RUN}; echo \\"'),
    ("a run inside a command substitution", f'echo "$({DEV_RUN})"'),
):
    expect(f"dev-backend-guard: {label} is blocked", run_hook("dev-backend-guard.py", {"tool_name": "Bash", "tool_input": {"command": cmd}}), 2)

# --- git-workdir-guard ---

with tempfile.TemporaryDirectory() as tmp:
    tmpdir = Path(tmp)
    repos = {}
    for name in ("repo_a", "repo_b"):
        repos[name] = tmpdir / name
        repos[name].mkdir()
        subprocess.run(["git", "init", "-q"], cwd=repos[name], check=True)
    env = {"CLAUDE_PROJECT_DIR": str(repos["repo_a"])}
    env.pop("CLAUDE_GIT_WORKDIR_GUARD_BYPASS", None)
    base = {"tool_name": "Bash", "cwd": str(repos["repo_a"])}
    b = str(repos["repo_b"]).replace("\\", "/")
    expect(
        "git-workdir-guard: a cd named inside a quoted echo does not repin the cwd",
        run_hook("git-workdir-guard.py", {**base, "tool_input": {"command": f'echo "x; cd {b}; y" ; git commit -m z'}}, env),
        0,
    )
    expect(
        "git-workdir-guard: a real chained cd into another repo is still caught",
        run_hook("git-workdir-guard.py", {**base, "tool_input": {"command": f"echo x; cd {b}; git commit -m z"}}, env),
        2,
    )
    expect(
        "git-workdir-guard: a commit inside a bash -c body after a cd is caught",
        run_hook("git-workdir-guard.py", {**base, "tool_input": {"command": f'cd {b}; bash -c "echo x; git commit -m z"'}}, env),
        2,
    )
    expect(
        "git-workdir-guard: a cd inside a bash -c body is caught for the commit that follows it there",
        run_hook("git-workdir-guard.py", {**base, "tool_input": {"command": f'bash -c "cd {b} && git commit -m z"'}}, env),
        2,
    )
    expect(
        "git-workdir-guard: a cd inside a bash -c body does not move the cwd of the parent's commit",
        run_hook("git-workdir-guard.py", {**base, "tool_input": {"command": f'bash -c "cd {b}"; git commit -m z'}}, env),
        0,
    )
    expect(
        "git-workdir-guard: a commit between two escaped quotes is caught",
        run_hook("git-workdir-guard.py", {**base, "tool_input": {"command": f'cd {b}; echo \\"; git commit -m z; echo \\"'}}, env),
        2,
    )

# --- push-gate (target resolution) ---

pg = _testlib.load_module("push_gate_q", _HOOKS_DIR / "push-gate.py")
expect(
    "push-gate: a cd named inside a quoted commit message does not repin the push target",
    pg.resolve_push_target('git commit -m "a; cd C:/other; b" && git push', "C:/cwd"),
    "C:/cwd",
)
expect("push-gate: a real chained cd still repins the push target", pg.resolve_push_target("cd C:/other; git push", "C:/cwd"), "C:/other")
expect(
    "push-gate: a git -C named inside a quoted string is not the push's -C",
    pg.git_dash_c_path('echo "x; git -C C:/o push; y"'),
    None,
)

# --- push-read-gate (read marker) ---

prg = _testlib.load_module("push_read_gate_q", _HOOKS_DIR / "push-read-gate.py")
expect(
    "push-read-gate: a cat of the snippet named inside a quoted grep does not satisfy the gate",
    prg.is_shell_read_of_auto_commit('git log --grep="a; cat snippets/auto-commit.md; b"'),
    False,
)
expect(
    "push-read-gate: a real chained cat of the snippet still satisfies the gate",
    prg.is_shell_read_of_auto_commit("echo x; cat snippets/auto-commit.md"),
    True,
)

sys.exit(_testlib.summarize(fails))
