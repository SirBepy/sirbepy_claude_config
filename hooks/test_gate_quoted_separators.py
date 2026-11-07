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
