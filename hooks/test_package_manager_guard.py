"""Self-test for package-manager-guard.py.

Run directly: python hooks/test_package_manager_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

Covers the pure classify/mutating/nearest-package.json helpers plus a full
main() pass with a temp package.json, no network and no live git/npm/yarn
invocation anywhere - `read_payload` is monkeypatched exactly like todo 803's
flutter-workdir-guard suite. Also pins `strip_quotes as _lib_strip_quotes`
from `hooks/_hooklib.py` as an explicit case: this import is the one a
mechanical dead-symbol scan almost deleted (todo 501's own incident), which
would silently trip this guard's fail-closed except-block for every
npm/yarn/pnpm call.
"""

import sys
import tempfile
from pathlib import Path

import _testlib

guard = _testlib.load_module(
    "guard", Path(__file__).resolve().parent / "package-manager-guard.py"
)

# --- pin the aliased _hooklib import (todo 501 incident) ---

alias_ok = (
    guard._lib_strip_quotes('"foo"') == "foo"
    and guard._lib_strip_quotes("'bar'") == "bar"
    and guard._lib_strip_quotes("baz") == "baz"
)
fails = []
if not _testlib.report(
    alias_ok, "strip_quotes as _lib_strip_quotes from _hooklib is imported and works"
):
    fails.append("strip_quotes alias")

# --- classify_invocation: manager, subcommand, info-flag, corepack-prefix ---

CLASSIFY_CASES = [
    (["npm", "install"], 0, ("npm", "install", False, False), "npm install"),
    (["corepack", "yarn", "add", "foo"], 1, ("yarn", "add", False, True), "corepack yarn add"),
    (["yarn", "--version"], 0, ("yarn", None, True, False), "yarn --version has no subcommand"),
    (
        ["pnpm", "--cwd", "sub", "update"],
        0,
        ("pnpm", "update", False, False),
        "pnpm --cwd sub update skips the cwd flag's value",
    ),
    (["yarn"], 0, ("yarn", None, False, False), "bare yarn, nothing follows"),
]


def check_classify(case) -> bool:
    tokens, idx, expected, label = case
    got = guard.classify_invocation(tokens, idx)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(CLASSIFY_CASES, check_classify)

# --- is_mutating: per-manager subcommand sets, plus yarn's bare-invocation rule ---

MUTATING_CASES = [
    ("npm", "install", False, True, "npm install mutates"),
    ("npm", "run", False, False, "npm run is read-only, out of scope"),
    ("yarn", None, False, True, "bare yarn defaults to install"),
    ("yarn", None, True, False, "yarn --version is info-only, not mutating"),
    ("pnpm", None, False, False, "bare pnpm does not default to install"),
    ("pnpm", "add", False, True, "pnpm add mutates"),
]


def check_mutating(case) -> bool:
    manager, subcommand, info_only, expected, label = case
    got = guard.is_mutating(manager, subcommand, info_only)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(MUTATING_CASES, check_mutating)

# --- find_nearest_package_json / read_package_manager, real temp files only ---

with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "package.json").write_text(
        '{"packageManager": "yarn@4.9.3"}', encoding="utf-8"
    )
    sub = root / "sub" / "deeper"
    sub.mkdir(parents=True)

    found = guard.find_nearest_package_json(sub)
    if not _testlib.report(found == root / "package.json", "walks up to the nearest package.json"):
        fails.append("nearest package.json")

    pinned = guard.read_package_manager(found)
    if not _testlib.report(pinned == ("yarn", "4.9.3"), "reads packageManager name+version"):
        fails.append("read_package_manager parses name+version")

    bad = root / "malformed.json"
    bad.write_text("{not json", encoding="utf-8")
    if not _testlib.report(
        guard.read_package_manager(bad) is None, "malformed package.json returns None, not a crash"
    ):
        fails.append("malformed package.json")

    no_field = root / "no_field.json"
    no_field.write_text("{}", encoding="utf-8")
    if not _testlib.report(
        guard.read_package_manager(no_field) is None, "package.json with no packageManager returns None"
    ):
        fails.append("no packageManager field")

# --- main() end to end: temp package.json, monkeypatched read_payload only ---


def run_main(command: str, cwd: str) -> int:
    guard.read_payload = lambda: {"tool_input": {"command": command}, "cwd": cwd}
    try:
        guard.main()
        return 0
    except SystemExit as e:
        return e.code


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    (root / "package.json").write_text(
        '{"packageManager": "yarn@4.9.3"}', encoding="utf-8"
    )

    MAIN_CASES = [
        ("yarn install", root, 2, "bare yarn install in a yarn-pinned dir is blocked"),
        ("corepack yarn install", root, 0, "corepack yarn install matches the pin"),
        ("npm install", root, 2, "npm install in a yarn-pinned dir is blocked, wrong manager"),
        ("corepack npm install", root, 2, "corepack npm in a yarn-pinned dir is still wrong manager"),
        ("yarn run build", root, 0, "yarn run is read-only, out of scope"),
        ("git status", root, 0, "unrelated command is untouched"),
    ]

    def check_main(case) -> bool:
        command, cwd, expected, label = case
        got = run_main(command, str(cwd))
        ok = got == expected
        print(f"{'PASS' if ok else 'FAIL'}: {label} (expected exit={expected}, got {got})")
        return ok

    fails += _testlib.run_cases(MAIN_CASES, check_main)

with tempfile.TemporaryDirectory() as tmp:
    # No package.json anywhere under this dir - guard must allow silently.
    got = run_main("yarn install", tmp)
    if not _testlib.report(got == 0, "yarn install with no package.json anywhere is allowed"):
        fails.append("no package.json allows")

sys.exit(_testlib.summarize(fails, style="count"))
