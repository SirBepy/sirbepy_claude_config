"""Self-test for cargo-test-pipe-guard.py (todo 780, extended by todo 877,
quote-position fix by todo 881; also covers the piped commit-pathspec.sh case).

Run directly: python hooks/test_cargo_test_pipe_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import sys
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "cargo-test-pipe-guard.py"
)

# (command, expect_block, label). expect_block=False means it must PASS through.
CASES = [
    ("cargo test --lib 2>&1 | tail -25", True, "acceptance: cargo test | tail is blocked"),
    (
        "cargo build --manifest-path src-tauri/Cargo.toml 2>&1 | tail -5",
        True,
        "2026-09-02 repro: cargo build piped into tail",
    ),
    (
        "cargo test --test daemon_user_todos_e2e --manifest-path Cargo.toml 2>&1 | tail -40",
        True,
        "2026-08-19 repro: cargo test with --test flag piped into tail",
    ),
    (
        "cargo test --manifest-path src-tauri/Cargo.toml --lib 2>&1 | tail -25",
        True,
        "2026-08-25 repro: cargo test --lib piped into tail",
    ),
    ("cargo test | head -20", True, "head is also a blocked filter"),
    ("cargo test 2>&1 | grep FAILED", True, "grep is also a blocked filter"),
    ("cargo test --lib 2>&1 | Select-Object -First 20", True, "PowerShell Select-Object is also blocked"),
    ("cargo check | tail", True, "todo 877: cargo check | tail is now blocked"),
    ("cargo clippy | tail", True, "todo 877: cargo clippy | tail is now blocked"),
    ("cargo check --lib 2>&1 | head -20", True, "cargo check with flags piped into head"),
    ("cargo clippy --all-targets 2>&1 | grep warning", True, "cargo clippy piped into grep"),
    ("cargo build", False, "bare cargo build with no pipe at all"),
    ("cargo check", False, "bare cargo check with no pipe at all"),
    ("tail -20 cargo-output.log", False, "carve-out: reading an already-finished output file"),
    (
        "cargo test --lib 2>&1 > cargo-output.log; tail -20 cargo-output.log",
        False,
        "carve-out: redirect to file then tail it in a separate statement",
    ),
    (
        "cargo test --lib 2>&1 | grep --line-buffered 'test result'",
        False,
        "carve-out: grep --line-buffered flushes per line, doesn't swallow",
    ),
    (
        "cargo test --lib 2>&1 | grep 'test result'",
        True,
        "grep without --line-buffered still blocked",
    ),
    ("cargo test | sort | tail -5", True, "filter two segments downstream of cargo test still blocked"),
    ("grep 'cargo test' notes.txt", False, "mentioning cargo test as a grep pattern, not running it"),
    (
        "flutter run --dart-define-from-file=.env.dev | tail",
        False,
        "trust boundary: a dev-server launch is not a cargo test command",
    ),
    ("npm run dev | tail -f", False, "trust boundary: unrelated dev command piped to tail"),
    ("cargo test", False, "bare cargo test with no pipe at all"),
    ("cargo test --lib", False, "cargo test with flags, no pipe at all"),
    (
        '''echo '{"tool_name":"Bash","tool_input":{"command":"cargo test --lib 2>&1 | tail -25"}}' | python hooks/cargo-test-pipe-guard.py''',
        False,
        "todo 881 repro: cargo test | tail quoted inside a JSON payload string, not run",
    ),
    (
        'git commit -m "docs: explain why cargo test --lib 2>&1 | tail -25 is blocked"',
        False,
        "todo 881: commit message quoting the piped-cargo-test example doesn't block the commit",
    ),
    # todo 934: _strip_leading_prefix only stripped sudo/VAR=val, so a filter
    # behind env/nohup/etc slipped past the todo-908 anchoring.
    ("cargo test | env FOO=BAR tail -40", True, "todo 934 repro: filter behind env is now blocked"),
    ("cargo test 2>&1 | nohup tail -f", True, "todo 934: filter behind nohup is now blocked"),
    ("cargo test | env FOO=BAR nohup tail -40", True, "todo 934: stacked env + nohup wrappers still caught"),
    ("cargo test | xargs echo tail", False, "todo 908 regression guard: tail as an xargs argument, not the filter itself, still passes"),
    # A separator inside quotes is data, not a pipeline; a shell -c argument is a command line.
    ('grep -E "cache|cargo build|tauri build" file', False, "quoted grep pattern holding |cargo build is not a piped build"),
    ('grep -E "a|cargo test|tail" file', False, "quoted grep pattern holding cargo test and tail is not a pipeline"),
    ("grep -E 'a|cargo check|head' file", False, "single-quoted grep pattern is not a pipeline either"),
    ('git commit -m "wip; cargo test | tail" -- f', False, "cargo test | tail named inside a commit message"),
    ('echo "run cargo build | tail"', False, "piped cargo build named inside an echo"),
    ('cargo test -- "a|b" | tail', True, "a quoted pipe in cargo's own args does not hide the real pipe"),
    ('bash -c "cargo test | tail"', True, "bash -c with a piped cargo test is still blocked"),
    ("bash -c 'cargo test 2>&1 | tail -5'", True, "single-quoted bash -c argument is still scanned"),
    ('pwsh -NoProfile -Command "cargo build | Select-Object -First 3"', True, "pwsh -Command argument is still scanned"),
    ('bash -c "bash -c \'cargo check | head\'"', True, "a nested -c wrapper is still scanned"),
    ('bash -c "cd \\"C:/a b\\" && cargo test | tail"', True, "escaped quotes inside a bash -c body do not cut the scan short"),
    ('bash -c "echo \\"x\\"; cargo test | tail"', True, "an escaped-quote statement before the pipe in a bash -c body"),
    ('echo "bash -c \'cargo test | tail\'"', False, "a bash -c named inside an echo is prose, not a wrapper"),
    ("echo it's; cargo test | tail", True, "an unbalanced quote falls back to the plain split and still sees the pipe"),
    ("cargo test |& tail", True, "|& (stderr too) into tail is still a pipe"),
    # commit-pathspec.sh: a piped filter swallows the script's own non-zero
    # exit, so a refused commit reads as success.
    (
        'bash ~/.claude/skills/commit/commit-pathspec.sh -m "FIX: a; b" f.txt 2>&1 | tail -6',
        True,
        "commit-pathspec: a semicolon inside the -m text does not hide the piped tail (2026-11-03)",
    ),
    ("bash commit-pathspec.sh -m x -- f |& tail -3", True, "commit-pathspec: |& into tail is blocked"),
    ("(bash commit-pathspec.sh -m x -- f) | tail -3", True, "commit-pathspec: a subshell-wrapped call piped into tail is blocked"),
    ("bash commit-pathspec.sh -m x -- f | tee commit.log", True, "commit-pathspec: tee swallows the exit code too"),
    ("bash commit-pathspec.sh -m x -- f | cat", True, "commit-pathspec: cat swallows the exit code too"),
    ("bash commit-pathspec.sh -m x -- f | sed -n 1,5p", True, "commit-pathspec: sed swallows the exit code too"),
    ("bash -c 'bash commit-pathspec.sh -m x -- f | tail -3'", True, "commit-pathspec: a piped call inside bash -c is blocked"),
    ('bash commit-pathspec.sh -m "a | tail" -- f', False, "commit-pathspec: a pipe inside the -m text is not a pipe"),
    (
        'echo "bash commit-pathspec.sh -m x -- f | tail"',
        False,
        "commit-pathspec: the whole piped call named inside an echo is prose",
    ),
    (
        "bash ~/.claude/skills/commit/commit-pathspec.sh -m x -- f | tail -3",
        True,
        "commit-pathspec: acceptance, piped into tail is blocked",
    ),
    (
        'bash "C:/Users/tecno/.claude/skills/commit/commit-pathspec.sh" -m x -- f 2>&1 | tail -6',
        True,
        "commit-pathspec: the 2026-10-22 shape (quoted script path, 2>&1, tail) is blocked",
    ),
    (
        "bash ~/.claude/skills/commit/commit-pathspec.sh -m x -- f | sort | head -2",
        True,
        "commit-pathspec: filter two segments downstream still blocked",
    ),
    (
        "bash commit-pathspec.sh -m x -- f | grep --line-buffered ok",
        True,
        "commit-pathspec: grep --line-buffered still swallows the exit code, so no carve-out",
    ),
    (
        "bash ~/.claude/skills/commit/commit-pathspec.sh -m x -- f | Select-Object -Last 3",
        True,
        "commit-pathspec: Select-Object is also a blocked filter",
    ),
    (
        "git status; bash ~/.claude/skills/commit/commit-pathspec.sh -m x -- f | tail",
        True,
        "commit-pathspec: piped call in a later statement is blocked",
    ),
    (
        "bash ~/.claude/skills/commit/commit-pathspec.sh -m x -- f",
        False,
        "commit-pathspec: unpiped call passes",
    ),
    (
        "bash ~/.claude/skills/commit/commit-pathspec.sh -m x -- f 2>&1",
        False,
        "commit-pathspec: stderr merge without a pipe passes",
    ),
    (
        "set -o pipefail; bash ~/.claude/skills/commit/commit-pathspec.sh -m x -- f | tail -3",
        False,
        "commit-pathspec: set -o pipefail first lets the pipe through",
    ),
    (
        "bash -o pipefail -c 'bash commit-pathspec.sh -m x -- f | tail -3'",
        False,
        "commit-pathspec: bash -o pipefail also counts",
    ),
    (
        "bash ~/.claude/skills/commit/commit-pathspec.sh -m x -- f; echo rc=$? | tail -1",
        False,
        "commit-pathspec: a filter after a later statement is not fed by the script",
    ),
    (
        "bash ~/.claude/skills/commit/commit-pathspec.sh -m x -- f > out.log; tail -3 out.log",
        False,
        "commit-pathspec: redirect to a file then tail it in a separate statement passes",
    ),
    (
        'git commit -m "docs: never pipe commit-pathspec.sh output | tail" -- f',
        False,
        "commit-pathspec: mention inside a quoted -m message passes",
    ),
    (
        '''echo '{"command":"bash commit-pathspec.sh -m x | tail"}' | python hook.py''',
        False,
        "commit-pathspec: mention inside a JSON payload string passes",
    ),
    (
        "cat ~/.claude/skills/commit/commit-pathspec.sh | head -20",
        False,
        "commit-pathspec: reading the script file is not running it",
    ),
    (
        "grep -n pipefail skills/commit/commit-pathspec.sh | head",
        False,
        "commit-pathspec: grep over the script file is not running it",
    ),
    # Command substitution runs even inside double quotes; eval and bash -ec bodies are command lines.
    ('out="$(cargo test 2>&1 | tail -5)"', True, "pc-review item 6: assignment of a double-quoted substitution"),
    ('echo "$(cargo build | tail -3)"', True, "pc-review item 6: substitution inside a double-quoted echo"),
    ('x=`cargo check | tail -2`', True, "backtick substitution"),
    ('bash -ec "cargo test | tail"', True, "bash -ec body is rescanned"),
    ('eval "cargo test 2>&1 | tail -5"', True, "eval body is rescanned"),
    ("eval 'cargo clippy | head'", True, "single-quoted eval body is rescanned"),
    ("echo '$(cargo test | tail)'", False, "single-quoted substitution is text, not a run"),
    ('echo "cargo test | tail"', False, "a quoted pipeline that is only printed stays allowed"),
    ('out="$(cargo test --lib 2>&1)"', False, "a substitution with no filter stays allowed"),
]


def check(case) -> bool:
    cmd, expect_block, label = case
    result = guard.find_violation(cmd) or guard.find_commit_pathspec_violation(cmd)
    got_block = result is not None
    ok = got_block == expect_block
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: {cmd!r} -> {'BLOCK' if got_block else 'PASS'} ({result})")
    return ok


def run() -> int:
    fails = _testlib.run_cases(CASES, check)
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
