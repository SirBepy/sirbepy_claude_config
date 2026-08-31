"""Self-test for dev-backend-guard.py.

Run directly: python hooks/test_dev_backend_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import subprocess
import sys
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "dev-backend-guard.py"

# (command, expect_block, label)
CASES = [
    # The two real incidents, 2026-08-25.
    (
        "fvm flutter run -d chrome --web-port=8082 --dart-define-from-file=.env.dev",
        True,
        "evening incident: flutter run against .env.dev",
    ),
    (
        "node run-all.js --target=dev",
        True,
        "morning incident: e2e suite against dev",
    ),
    (
        "E2E_TARGET=dev node run-all.js",
        True,
        "e2e target via env assignment",
    ),
    (
        'node e2e/run-all.js --target dev',
        True,
        "e2e target as a separate argument",
    ),
    # Local is the whole point of the guard, it must never be blocked.
    (
        "fvm flutter run -d chrome --web-port=8080 --dart-define-from-file=.env.local",
        False,
        "flutter run against .env.local",
    ),
    ("node run-all.js --target=local", False, "e2e suite against local"),
    ("node run-all.js", False, "e2e suite with no target, defaults to local"),
    # `--target` belongs to tsc/cargo/docker/vite too, and those runs are not e2e.
    (
        "npm run build --target=production",
        False,
        "npm build with an unrelated --target",
    ),
    ("pnpm vite build --target es2020", False, "vite --target is not an e2e target"),
    ("docker build --target=builder -t app .", False, "docker --target is not an e2e target"),
    ("npm run test:e2e -- --target=dev", True, "e2e npm script against dev still blocks"),
    # Ordinary work must stay unblocked or the hook gets switched off.
    ("fvm flutter analyze", False, "bare analyze"),
    ("fvm flutter test", False, "bare test"),
    ("git commit -m 'fix'", False, "unrelated command"),
    # Mentioning dev without driving anything only warns.
    ("cat .env.dev", False, "reading the dev env file"),
    ("grep -n API_URL .env.dev", False, "grepping the dev env file"),
    ("curl -sI https://dev.pay.zirtue.com", False, "read-only probe of the dev host"),
    # Chained commands: the block must survive a leading cd.
    (
        'cd "C:/repo" && fvm flutter run --dart-define-from-file=.env.dev',
        True,
        "cd then flutter run against dev",
    ),
]


def check(case) -> bool:
    command, expect_block, _label = case
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    proc = subprocess.run(
        [sys.executable, str(_GUARD_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    blocked = proc.returncode != 0
    return blocked == expect_block


def main() -> int:
    fails = []
    for case in CASES:
        ok = check(case)
        if not _testlib.report(ok, case[2]):
            fails.append(case[2])
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(main())
