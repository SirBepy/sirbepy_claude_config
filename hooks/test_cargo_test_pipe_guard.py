"""Self-test for cargo-test-pipe-guard.py (todo 780, extended by todo 877,
quote-position fix by todo 881).

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
]


def check(case) -> bool:
    cmd, expect_block, label = case
    result = guard.find_violation(cmd)
    got_block = result is not None
    ok = got_block == expect_block
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: {cmd!r} -> {'BLOCK' if got_block else 'PASS'} ({result})")
    return ok


def run() -> int:
    fails = _testlib.run_cases(CASES, check)
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
