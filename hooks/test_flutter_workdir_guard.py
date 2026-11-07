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
import tempfile
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
    (
        "PowerShell",
        'grep -E "foo|flutter run" f',
        False,
        "flutter after a pipe inside a quoted pattern via PowerShell does not warn",
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
    # Chain splitting is quote-aware: a pipe inside a quoted grep -E alternation
    # is part of the pattern, not a pipeline boundary.
    (
        "Bash",
        'F="out.txt"; sed \'s/\\x1b\\[[0-9;]*[A-Za-z]//g\' "$F" | grep -a -n -E "FILE-|JUnit totals|flutter  " | cut -c1-200',
        0,
        "flutter as the last alternative of a quoted grep -E pattern via Bash is allowed",
    ),
    ("Bash", 'grep -E "foo|dart run" f', 0, "dart after a quoted pipe via Bash is allowed"),
    ("Bash", "flutter --version | head -3", 2, "flutter leading a real pipeline via Bash stays denied"),
    ("Bash", "cat f | flutter analyze", 2, "flutter after an unquoted pipe via Bash stays denied"),
    (
        "Bash",
        'echo "a; b | c" && flutter analyze',
        2,
        "a quoted semicolon and pipe do not hide a real flutter after an unquoted separator",
    ),
    ("Bash", "echo hi & flutter analyze", 2, "flutter after a single ampersand via Bash stays denied"),
    (
        "PowerShell",
        'grep -E "foo|dart run build_runner build --delete-conflicting-outputs" f',
        0,
        "a destructive command named only inside a quoted pattern is not blocked",
    ),
    (
        "PowerShell",
        'Select-String "a|b" f; dart run build_runner build --delete-conflicting-outputs',
        2,
        "an unpinned destructive build_runner after a quoted-pipe segment stays blocked",
    ),
    (
        "PowerShell",
        "& fvm flutter pub run build_runner build --delete-conflicting-outputs",
        2,
        "the PowerShell call operator before fvm still reaches the destructive-flag block",
    ),
    # An escaped quote desyncs the quote scan; the split falls back to plain separators.
    ("Bash", 'echo "a\\" b"; fvm flutter build', 2, "fvm after a backslash-escaped quote via Bash stays denied"),
    # A shell -c argument is a command line, not prose.
    (
        "PowerShell",
        'bash -c "cd x; dart run build_runner build --delete-conflicting-outputs"',
        2,
        "an unpinned destructive build_runner inside bash -c is still blocked",
    ),
    ("Bash", 'bash -c "fvm flutter test"', 2, "fvm leading a bash -c body via Bash is denied"),
    (
        "PowerShell",
        'echo "bash -c \'dart run build_runner build --delete-conflicting-outputs\'"',
        0,
        "a bash -c named only inside an echo is prose, not a wrapper",
    ),
    # A PowerShell body run from the Bash tool is already PowerShell: the deny message's own fix.
    ("Bash", 'pwsh -Command "fvm flutter analyze"', 0, "pc-review item 7: pwsh -Command body is not a leading Bash command"),
    ("Bash", 'powershell -Command "fvm dart test"', 0, "pc-review item 7: powershell -Command body is not a leading Bash command"),
    ("Bash", 'pwsh -NoProfile -c "fvm flutter test"', 0, "pwsh -NoProfile -c body is not a leading Bash command"),
    ("Bash", 'cmd /c "fvm flutter test"', 0, "cmd /c body is not a leading Bash command"),
    ("Bash", 'bash -c "pwsh -Command \'fvm flutter test\'"', 0, "a pwsh body nested in a bash body is still PowerShell"),
    ("Bash", 'bash -ec "fvm flutter test"', 2, "fvm leading a bash -ec body is still denied"),
    ("Bash", 'pwsh -Command "echo ok"; fvm flutter test', 2, "a real leading fvm after a pwsh statement is still denied"),
    (
        "Bash",
        'pwsh -Command "dart run build_runner build --delete-conflicting-outputs"',
        2,
        "an unpinned destructive build_runner in a pwsh body is still blocked",
    ),
]

# A Git Bash `cd /c/...` pin must reach the same pubspec.yaml check as `cd C:/...`
# (Windows only: elsewhere `/c/...` is a real path, not a drive alias).
_msys_project = tempfile.TemporaryDirectory()
if os.name == "nt":
    (Path(_msys_project.name) / "pubspec.yaml").write_text("name: x\n", encoding="utf-8")
    _posix = Path(_msys_project.name).as_posix()
    _msys = f"/{_posix[0].lower()}{_posix[2:]}"
    _cmd = f"cd {_msys}; dart run build_runner build --delete-conflicting-outputs"
    CASES.append(("PowerShell", _cmd, 0, "a Git Bash /c/ cd pin onto a real Flutter project counts as pinned"))


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
    _msys_project.cleanup()
    if saved_bypass is not None:
        os.environ[guard.OVERRIDE_ENV] = saved_bypass

sys.exit(_testlib.summarize(fails, style="count"))
