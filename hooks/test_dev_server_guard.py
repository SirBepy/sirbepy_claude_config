"""Self-test for dev-server-guard.py.

Run directly: python hooks/test_dev_server_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

The negatives carry the weight (todo 441): `npm test` and `npm run build`
must pass so a naive `npm run` match never blocks the test floor, a real
`sv.ps1 ensure ...` invocation (the exact shape from SKILL.md:36) must pass
even though its own -Cmd argument contains "vite", and a `cargo test` must
pass so this guard never fires on a sibling guard's own trigger pattern.
"""

import sys
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "dev-server-guard.py"
)

fails = []

# --- invokes_supervisor: the crux distinguisher ---

SUPERVISOR_CASES = [
    (
        ['powershell', '-File', 'C:/Users/tecno/.claude/skills/supervised-run/sv.ps1',
         'ensure', '-Project', 'frontend', '-Cmd', 'vite --port {PORT}'],
        True,
        "sv.ps1 ensure invocation is recognized as supervised",
    ),
    (['sv.ps1', 'ls'], True, "any sv.ps1 subcommand counts, not only ensure"),
    (['vite', '--port', '3000'], False, "raw vite has no sv.ps1 token"),
]


def check_supervisor(case) -> bool:
    tokens, expected, label = case
    got = guard.invokes_supervisor(tokens)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(SUPERVISOR_CASES, check_supervisor)

# --- is_dev_server_command: positives and negatives ---

MATCH_CASES = [
    (['vite'], 'vite', "bare vite matches"),
    (['npx', 'vite', '--port', '3000'], 'vite', "npx vite matches"),
    (['vite', 'build'], None, "vite build is a one-off, not matched"),
    (['next', 'dev'], 'next dev', "next dev matches"),
    (['next', 'build'], None, "next build is a one-off, not matched"),
    (['next', 'start'], 'next start', "next start matches"),
    (['vite', 'preview'], 'vite', "vite preview matches"),
    (['dart', 'run', 'bin/server.dart'], None, "dart run is deliberately uncovered"),
    (['npm', 'run', 'dev'], 'npm run dev', "npm run dev matches"),
    (['npm', 'test'], None, "npm test is out of scope"),
    (['npm', 'run', 'build'], None, "npm run build is a one-off, not matched"),
    (['pnpm', 'dev'], 'pnpm dev', "pnpm dev shorthand matches"),
    (['yarn', 'dev'], 'yarn dev', "yarn dev shorthand matches"),
    (['flutter', 'run'], 'flutter run', "flutter run matches"),
    (['flutter', 'test'], None, "flutter test is out of scope"),
    (['uvicorn', 'app:app', '--reload'], 'uvicorn', "uvicorn matches"),
    (['fastify', 'start', 'server.js'], 'fastify', "fastify start matches"),
    (['cargo', 'tauri', 'dev'], 'tauri dev', "cargo tauri dev matches"),
    (['npm', 'run', 'tauri', 'dev'], 'tauri dev', "npm run tauri dev matches"),
    (['cargo', 'test'], None, "cargo test never matches (sibling guard's trigger)"),
    (['git', 'status'], None, "unrelated command is untouched"),
    (['uvicorn', '--version'], None, "an info flag is never mistaken for a launch"),
]


def check_match(case) -> bool:
    tokens, expected, label = case
    got = guard.is_dev_server_command(tokens)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(MATCH_CASES, check_match)

# --- main() end to end, monkeypatched read_payload only ---


def run_main(command: str) -> int:
    guard.read_payload = lambda: {"tool_input": {"command": command}, "cwd": "."}
    try:
        guard.main()
        return 0
    except SystemExit as e:
        return e.code


MAIN_CASES = [
    ("npm test", 0, "npm test passes"),
    ("npm run build", 0, "npm run build passes"),
    ("cargo test", 0, "cargo test passes"),
    ("git status", 0, "unrelated command passes"),
    (
        'powershell -File "C:\\Users\\tecno\\.claude\\skills\\supervised-run\\sv.ps1" '
        'ensure -Project frontend -Cmd "vite --port {PORT}"',
        0,
        "a real sv.ps1 ensure invocation passes even though its -Cmd mentions vite",
    ),
    ("vite", 2, "raw vite is caught"),
    ("vite --port 3000", 2, "raw vite with flags is caught"),
    ("npm run dev", 2, "raw npm run dev is caught"),
    ("pnpm dev", 2, "raw pnpm dev is caught"),
    ("flutter run -d chrome", 2, "raw flutter run is caught"),
    ("uvicorn app:app --reload", 2, "raw uvicorn is caught"),
    ("cargo tauri dev", 2, "raw cargo tauri dev is caught"),
    ("next start", 2, "raw next start is caught"),
    ("vite preview", 2, "raw vite preview is caught"),
    ("dart run bin/server.dart", 0, "raw dart run passes, deliberately uncovered"),
]


def check_main(case) -> bool:
    command, expected, label = case
    got = run_main(command)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected exit={expected}, got {got})")
    return ok


fails += _testlib.run_cases(MAIN_CASES, check_main)

sys.exit(_testlib.summarize(fails, style="count"))
