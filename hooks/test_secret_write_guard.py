"""Self-test for secret-write-guard.py (todo 420).

Run directly: python hooks/test_secret_write_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import _testlib

HOOKS_DIR = Path(__file__).resolve().parent

# Every fake credential below is SPLIT across a concatenation on purpose. The
# runtime string is identical, but no source LINE holds a complete match, so
# skills/commit/secret-scan.sh does not flag this suite at commit time.
AKIA = "AKIA" + "IOSFODNN7EXAMPLE"
AWS_LONG_B64 = "wJalrXUtnFEMI/K7MDENG" + "/bPxRfiCYEXAMPLEKEY"
GH_TOKEN = "ghp_" + "abcdefghijklmnopqrstuvwxyz0123456789"
SK_KEY = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
SLACK = "xoxb-" + "111111111111-222222222222-abcdefghijklmnop"
PEM = "-----BEGIN RSA " + "PRIVATE KEY-----"
CONN = "postgres://admin:" + "realpassword123" + "@db.internal:5432/app"
PLAIN_LITERAL = "hunter2" + "hunter2"
FIREBASE_KEY = "AIza" + "SyCMxWyGRJScXgsl1qa_nNbUdIs5o86w83Y"
FIREBASE_KEY_TOO_LONG = FIREBASE_KEY + "x"
MIDSTRING_NOT = "cannot-" + "be-rotated-abc123xyz"

# (content, expect_hit, label). One positive + one negative per pattern row
# in secret-patterns.txt, plus the negative cases the spec calls out by name.
CASES = [
    (f"aws_access_key_id = {AKIA}", True, "aws_akia: real key"),
    ("aws_access_key_id = my-app-key", False, "aws_akia: unrelated value"),
    (f'aws_secret_access_key = "{AWS_LONG_B64}"', True, "aws_secret: 40-char b64"),
    ("aws_secret_access_key short", False, "aws_secret: too short"),
    (f"token = {GH_TOKEN}", True, "github_token: ghp_"),
    ("token = ghz_abcdefghijklmnopqrstuvwxyz0123456789", False, "github_token: wrong prefix"),
    (f'apiKey: "{SK_KEY}"', True, "sk_key: openai-shaped"),
    ('label: "desk-organizer-with-long-name-here"', False, "sk_key: desk- must not match"),
    (f"token = {SLACK}", True, "slack_token: xoxb"),
    ("token = xoyb-111111111111-222222222222-abcdefghijklmnop", False, "slack_token: wrong prefix"),
    (PEM, True, "private_key_block: RSA"),
    ("-----BEGIN CERTIFICATE-----", False, "private_key_block: not a private key"),
    (CONN, True, "conn_string_creds: real creds"),
    ("postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:5432/db", False, "conn_string_creds: interpolated template"),
    (f'password = "{PLAIN_LITERAL}"', True, "generic_assignment: real literal"),
    ('password = "changeme"', False, "generic_assignment: placeholder"),
    ('token: "not-the-real-token"', False, "generic_assignment: leading not- placeholder (todo 471)"),
    ('token = "fake-oauth-secret-abc123"', False, "generic_assignment: leading fake- placeholder (todo 471)"),
    (
        f'token = "{MIDSTRING_NOT}"',
        True,
        "generic_assignment: not- allow is leading-anchor only, mid-value not- still trips",
    ),
    ("const x = process.env.AWS_KEY;", False, "generic_assignment: process.env excluded"),
    ('api_key = os.environ["API_KEY"]', False, "generic_assignment: os.environ excluded"),
    ('token: "<your-token-here>"', False, "generic_assignment: angle-bracket placeholder"),
    ('token = "${TOKEN}"', False, "generic_assignment: quoted env-ref value excluded"),
    ('console.log("LOCALSTORAGE_TOKEN:", await evalJs(() => x))', False, "generic_assignment: comma/paren spanning quotes"),
    (f"apiKey: '{FIREBASE_KEY}'", False, "generic_assignment: firebase web api key allowed (todo 833)"),
    (f"apiKey: '{FIREBASE_KEY_TOO_LONG}'", True, "generic_assignment: firebase-shaped value one char too long still trips"),
    (f"apiKey: '{FIREBASE_KEY}'\naws_access_key_id = {AKIA}", True, "firebase key alongside a real AWS key in the same file: AWS key still trips"),
]


def check(case) -> bool:
    content, expect_hit, label = case
    payload = json.dumps({"tool_input": {"file_path": "scratch.txt", "content": content}})
    proc = subprocess.run(
        [sys.executable, str(HOOKS_DIR / "secret-write-guard.py")],
        input=payload, capture_output=True, text=True,
    )
    got_hit = "\"permissionDecision\": \"ask\"" in proc.stdout
    ok = got_hit == expect_hit and proc.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: hit={got_hit} rc={proc.returncode} {content!r}")
    return ok


def check_env_example_write() -> bool:
    payload = json.dumps({"tool_input": {"file_path": ".env.example", "content": "API_KEY=changeme"}})
    proc = subprocess.run(
        [sys.executable, str(HOOKS_DIR / "secret-write-guard.py")],
        input=payload, capture_output=True, text=True,
    )
    ok = "ask" not in proc.stdout and proc.returncode == 0
    return _testlib.report(ok, "secret-write-guard is content-based: .env.example write with placeholder value passes clean")


def check_ask_json_shape() -> bool:
    payload = json.dumps({"tool_input": {"file_path": "x.txt", "content": AKIA}})
    proc = subprocess.run(
        [sys.executable, str(HOOKS_DIR / "secret-write-guard.py")],
        input=payload, capture_output=True, text=True,
    )
    data = json.loads(proc.stdout)
    ok = (
        proc.returncode == 0
        and data["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        and data["hookSpecificOutput"]["permissionDecision"] == "ask"
        and isinstance(data["hookSpecificOutput"]["permissionDecisionReason"], str)
    )
    return _testlib.report(ok, "ask output is valid JSON with permissionDecision=ask and exit 0")


def check_fails_open_on_garbage() -> bool:
    proc = subprocess.run(
        [sys.executable, str(HOOKS_DIR / "secret-write-guard.py")],
        input="not json {{{", capture_output=True, text=True,
    )
    return _testlib.report(proc.returncode == 0, "fails open on malformed stdin payload")


def check_fails_loud_on_missing_patterns() -> bool:
    real = HOOKS_DIR / "secret-patterns.txt"
    moved = HOOKS_DIR / "secret-patterns.txt.movedfortest"
    payload = json.dumps({"tool_input": {"file_path": "x.txt", "content": AKIA}})
    real.rename(moved)
    try:
        proc = subprocess.run(
            [sys.executable, str(HOOKS_DIR / "secret-write-guard.py")],
            input=payload, capture_output=True, text=True,
        )
    finally:
        moved.rename(real)
    ok = proc.returncode != 0
    return _testlib.report(ok, f"fails LOUD (exit {proc.returncode}) when pattern file is missing")


def check_no_posix_classes_and_all_compile() -> bool:
    """Scans only the ERE column (not the file's own explanatory comments,
    which name the forbidden [[:space:]] syntax as an example).
    """
    text = (HOOKS_DIR / "secret-patterns.txt").read_text(encoding="utf-8")
    has_posix = False
    all_compile = True
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = raw.split("\t")
        if len(parts) != 3:
            all_compile = False
            continue
        if "[[:" in parts[2]:
            has_posix = True
        try:
            re.compile(parts[2])
        except re.error:
            all_compile = False
    ok = not has_posix and all_compile
    return _testlib.report(ok, "secret-patterns.txt EREs have no POSIX bracket class and all compile under Python re")


def run() -> int:
    fails = _testlib.run_cases(CASES, check)
    for fn in (
        check_env_example_write,
        check_ask_json_shape,
        check_fails_open_on_garbage,
        check_fails_loud_on_missing_patterns,
        check_no_posix_classes_and_all_compile,
    ):
        if not fn():
            fails.append(fn.__name__)
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
