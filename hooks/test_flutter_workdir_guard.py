"""Self-test for flutter-workdir-guard.py.

Run directly: python hooks/test_flutter_workdir_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Covers the todo-803 addition (fvm/flutter/dart as the LEADING word of a
Bash-tool command is denied outright, PowerShell untouched) by driving the
real guard.main() with a monkeypatched read_payload - no subprocess, no
live fvm/flutter/dart, no network. The pre-existing destructive-flag/pin
logic already has coverage via done/380-era manual verification and is not
re-covered here beyond confirming this addition does not break its pass-
through cases.

Also covers todo 908: has_runner() anchored to command position so a
`grep -r "flutter" pubspec.yaml` no longer counts as a runner invocation.
"""

import contextlib
import io
import os
import sys
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "flutter-workdir-guard.py"
)


# --- pin the aliased _hooklib import (todo 501 incident: a mechanical dead-
# symbol scan almost deleted strip_quotes since it is imported under an alias) ---

alias_ok = (
    guard._lib_strip_quotes('"foo"') == "foo"
    and guard._lib_strip_quotes("'bar'") == "bar"
    and guard._lib_strip_quotes("baz") == "baz"
)
alias_fails = []
if not _testlib.report(
    alias_ok, "strip_quotes as _lib_strip_quotes from _hooklib is imported and works"
):
    alias_fails.append("strip_quotes alias")


def run_main(tool_name: str, command: str) -> int:
    guard.read_payload = lambda: {"tool_name": tool_name, "tool_input": {"command": command}}
    try:
        guard.main()
        return 0
    except SystemExit as e:
        return e.code


def run_main_captured(tool_name: str, command: str) -> tuple[int, str]:
    guard.read_payload = lambda: {"tool_name": tool_name, "tool_input": {"command": command}}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            guard.main()
            code = 0
        except SystemExit as e:
            code = e.code
    return code, buf.getvalue()


# --- has_runner: command-position anchoring (todo 908) ---

HAS_RUNNER_CASES = [
    (["flutter", "analyze"], True, "flutter as the leading token is a runner"),
    (["grep", "-r", "flutter", "pubspec.yaml"], False, "flutter as a grep pattern argument is not a runner"),
    (["echo", "flutter"], False, "flutter as a bare echo argument is not a runner"),
    (
        ["Start-Process", "-FilePath", "dart.bat", "-ArgumentList", "run", "build_runner", "build"],
        True,
        "dart.bat right after -FilePath is a runner (Start-Process pattern)",
    ),
    (
        ["fvm", "flutter", "pub", "run", "build_runner", "build"],
        True,
        "flutter after the fvm launcher is a runner (the primary form on this machine)",
    ),
    (
        ["&", "C:/tools/flutter.bat", "run", "build_runner", "build"],
        True,
        "flutter.bat after PowerShell's & call operator is a runner",
    ),
    (
        ["echo", "hi", "&", "flutter", "build"],
        True,
        "& separates commands in both PowerShell and cmd, so a runner after it is a real invocation",
    ),
    (
        ["echo", "fvm flutter build"],
        False,
        "a quoted string naming fvm flutter is one argument, not an invocation",
    ),
]


def check_has_runner(case) -> bool:
    tokens, expected, label = case
    got = guard.has_runner(tokens)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


has_runner_fails = _testlib.run_cases(HAS_RUNNER_CASES, check_has_runner)

# --- end to end: the grep-pubspec false positive prints no spurious warning ---

WARNING_CASES = [
    (
        "PowerShell",
        'grep -r "flutter" pubspec.yaml',
        False,
        "grep flutter pubspec.yaml via PowerShell warns about no directory pin",
    ),
    (
        "PowerShell",
        "flutter analyze",
        True,
        "a real bare flutter call via PowerShell still warns about no directory pin",
    ),
]


def check_warning(case) -> bool:
    tool_name, command, expect_warning, label = case
    code, out = run_main_captured(tool_name, command)
    got_warning = "Warning" in out
    ok = code == 0 and got_warning == expect_warning
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected warning={expect_warning}, got {got_warning}, exit={code})")
    return ok


warning_fails = _testlib.run_cases(WARNING_CASES, check_warning)


# (tool_name, command, expected exit code, label)
CASES = [
    ("Bash", "fvm flutter analyze", 2, "fvm flutter analyze via Bash is denied"),
    ("PowerShell", "fvm flutter analyze", 0, "fvm flutter analyze via PowerShell passes through untouched"),
    ("Bash", "flutter analyze", 2, "bare flutter via Bash is denied"),
    ("Bash", "dart test", 2, "bare dart via Bash is denied"),
    ("Bash", "grep flutter README.md", 0, "grep flutter README.md via Bash is allowed, not leading"),
    ("Bash", 'echo "run fvm"', 0, "echo run fvm via Bash is allowed, not leading and quoted"),
    (
        "Bash",
        "cd C:/repo && fvm flutter test",
        2,
        "fvm leading its own chained segment after cd is still denied",
    ),
    ("Bash", "git commit -m 'fix'", 0, "unrelated command via Bash is allowed"),
]


def check(case) -> bool:
    tool_name, command, expected, label = case
    got = run_main(tool_name, command)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected exit={expected}, got {got})")
    return ok


saved_bypass = os.environ.pop(guard.OVERRIDE_ENV, None)
try:
    fails = alias_fails + has_runner_fails + warning_fails + _testlib.run_cases(CASES, check)
finally:
    if saved_bypass is not None:
        os.environ[guard.OVERRIDE_ENV] = saved_bypass

sys.exit(_testlib.summarize(fails, style="count"))
