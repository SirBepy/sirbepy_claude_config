"""Self-test for sensitive-file-guard.py (todo 420).

Run directly: python hooks/test_sensitive_file_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import subprocess
import sys
from pathlib import Path

import _testlib

HOOKS_DIR = Path(__file__).resolve().parent
GUARD = HOOKS_DIR / "sensitive-file-guard.py"

# (file_path, expect_ask, label).
CASES = [
    (".env", True, "credential: bare .env"),
    (".env.local", True, "credential: .env.local"),
    (".env.example", False, "credential: .env.example is deliberately excluded"),
    ("server.pem", True, "credential: *.pem"),
    ("private.key", True, "credential: *.key"),
    ("bundle.p12", True, "credential: *.p12"),
    ("bundle.pfx", True, "credential: *.pfx"),
    ("id_rsa", True, "credential: id_rsa"),
    ("id_ed25519", True, "credential: id_ed25519"),
    ("credentials.json", True, "credential: credentials.json"),
    (".npmrc", True, "credential: .npmrc"),
    (".pypirc", True, "credential: .pypirc"),
    ("README.md", False, "credential: unrelated file"),
    ("package-lock.json", True, "lockfile: package-lock.json"),
    ("yarn.lock", True, "lockfile: yarn.lock"),
    ("pnpm-lock.yaml", True, "lockfile: pnpm-lock.yaml"),
    ("Cargo.lock", True, "lockfile: Cargo.lock"),
    ("poetry.lock", True, "lockfile: poetry.lock"),
    ("pubspec.lock", True, "lockfile: pubspec.lock"),
    ("Gemfile.lock", True, "lockfile: Gemfile.lock"),
    ("package.json", False, "lockfile: manifest itself is not a lockfile"),
    (r"C:\Users\tecno\.claude\hooks\secret-write-guard.py", True, "self-protect: hooks/ under repo root, backslashes"),
    ("some/project/.claude/hooks/foo.py", True, "self-protect: hooks/ under a project .claude/, forward slashes"),
    ("hooks/README.md", False, "self-protect: hooks-named dir with no leading .claude/ segment"),
    ("settings.json", True, "self-protect: settings.json"),
    ("settings.local.json", True, "self-protect: settings.local.json"),
    ("repo/.git/config", True, ".git internals: nested config"),
    (".git/HEAD", True, ".git internals: HEAD"),
    ("gitignore.md", False, ".git internals: filename merely contains 'git'"),
]


def check(case) -> bool:
    file_path, expect_ask, label = case
    payload = json.dumps({"tool_input": {"file_path": file_path, "content": "x"}})
    proc = subprocess.run([sys.executable, str(GUARD)], input=payload, capture_output=True, text=True)
    got_ask = "\"permissionDecision\": \"ask\"" in proc.stdout
    ok = got_ask == expect_ask and proc.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: ask={got_ask} rc={proc.returncode} {file_path!r}")
    return ok


def check_ask_json_shape() -> bool:
    payload = json.dumps({"tool_input": {"file_path": ".env", "content": "x"}})
    proc = subprocess.run([sys.executable, str(GUARD)], input=payload, capture_output=True, text=True)
    data = json.loads(proc.stdout)
    ok = (
        proc.returncode == 0
        and data["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        and data["hookSpecificOutput"]["permissionDecision"] == "ask"
        and isinstance(data["hookSpecificOutput"]["permissionDecisionReason"], str)
    )
    return _testlib.report(ok, "ask output is valid JSON with permissionDecision=ask and exit 0")


def check_fails_open_on_garbage() -> bool:
    proc = subprocess.run([sys.executable, str(GUARD)], input="not json {{{", capture_output=True, text=True)
    return _testlib.report(proc.returncode == 0, "fails open on malformed stdin payload")


def check_no_path_no_op() -> bool:
    payload = json.dumps({"tool_input": {"content": "x"}})
    proc = subprocess.run([sys.executable, str(GUARD)], input=payload, capture_output=True, text=True)
    ok = proc.returncode == 0 and proc.stdout.strip() == ""
    return _testlib.report(ok, "no file_path/notebook_path is a silent no-op")


def run() -> int:
    fails = _testlib.run_cases(CASES, check)
    for fn in (check_ask_json_shape, check_fails_open_on_garbage, check_no_path_no_op):
        if not fn():
            fails.append(fn.__name__)
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
