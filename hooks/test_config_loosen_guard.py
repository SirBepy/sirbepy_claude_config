"""Self-test for config-loosen-guard.py (todo 440).

Run directly: python hooks/test_config_loosen_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.

End-to-end cases run the guard as a real subprocess (payload on stdin, exit
code + stdout inspected) matching test_secret_write_guard.py's shape, since
that also exercises the malformed-payload / fail-open path for real rather
than by calling main() in-process.
"""

import json
import subprocess
import sys
from pathlib import Path

import _testlib

HOOKS_DIR = Path(__file__).resolve().parent
GUARD = HOOKS_DIR / "config-loosen-guard.py"

guard = _testlib.load_module("guard", GUARD)

fails = []

# --- classify_file: the file-set match, positives and negatives ---

CLASSIFY_CASES = [
    ("tsconfig.json", "tsconfig", "bare tsconfig.json"),
    ("tsconfig.base.json", "tsconfig", "tsconfig variant"),
    (".eslintrc", "eslintrc", "bare .eslintrc"),
    (".eslintrc.json", "eslintrc", ".eslintrc.json"),
    ("eslint.config.js", "eslintrc", "flat eslint config"),
    ("eslint.config.mts", "eslintrc", "flat eslint config, .mts"),
    ("biome.json", "biome", "biome.json"),
    ("biome.jsonc", "biome", "biome.jsonc"),
    ("analysis_options.yaml", "analysis_options", "Dart analysis_options.yaml"),
    ("pyproject.toml", "pyproject", "pyproject.toml"),
    ("Cargo.toml", "cargo", "Cargo.toml"),
    ("pubspec.yaml", "pubspec", "pubspec.yaml"),
    ("vitest.config.ts", "vitest", "vitest config"),
    ("jest.config.js", "jest", "jest config"),
    ("jest.config.json", "jest", "jest config json"),
    ("package.json", None, "package.json is not in the file set"),
    ("README.md", None, "unrelated file is not in the file set"),
    ("pubspec.lock", None, "pubspec.lock (not .yaml) is not matched here"),
]


def check_classify(case) -> bool:
    basename, expected, label = case
    got = guard.classify_file(basename)
    ok = got == expected
    print(f"{'PASS' if ok else 'FAIL'}: {label} (expected {expected}, got {got})")
    return ok


fails += _testlib.run_cases(CLASSIFY_CASES, check_classify)

# --- detect_loosening: unit-level, per file kind ---

DETECT_CASES = [
    (
        "tsconfig",
        {"old_string": '"strict": true,\n"target": "ES2020"', "new_string": '"strict": false,\n"target": "ES2020"'},
        True,
        "tsconfig: strict true -> false is caught",
    ),
    (
        "tsconfig",
        {"old_string": '"strict": true,', "new_string": ""},
        True,
        "tsconfig: strict:true line deleted outright is caught",
    ),
    (
        "tsconfig",
        {"old_string": '"target": "ES2020"', "new_string": '"target": "ES2022"'},
        False,
        "tsconfig: unrelated key (target) change is not caught",
    ),
    (
        "tsconfig",
        {"old_string": '"sourceMap": true,', "new_string": '"sourceMap": false,'},
        False,
        "tsconfig: sourceMap is not a strictness key, not caught",
    ),
    (
        "eslintrc",
        {"old_string": '"no-console": "error"', "new_string": '"no-console": "off"'},
        True,
        "eslintrc: rule error -> off is caught",
    ),
    (
        "eslintrc",
        {"old_string": '"no-console": "error"', "new_string": ""},
        True,
        "eslintrc: error-level rule line deleted outright is caught",
    ),
    (
        "eslintrc",
        {"old_string": '"rules": {}', "new_string": '"rules": {\n  "no-new-rule": "error"\n}'},
        False,
        "eslintrc: adding a brand-new error-level rule is not caught (nothing removed)",
    ),
    (
        "cargo",
        {"old_string": 'unused = "deny"', "new_string": 'unused = "allow"'},
        True,
        "cargo: lint deny -> allow is caught",
    ),
    (
        "cargo",
        {"old_string": '[dependencies]', "new_string": '[dependencies]\nserde = "1.0"'},
        False,
        "cargo: adding a dependency is not caught",
    ),
    (
        "cargo",
        {"old_string": '[profile.release]', "new_string": '[profile.release]\nopt-level = 2'},
        False,
        "cargo: an unrelated numeric profile setting is not caught (digits are eslint-only)",
    ),
    (
        "analysis_options",
        {"old_string": "strict-casts: true", "new_string": "strict-casts: false"},
        True,
        "analysis_options: strict-casts true -> false is caught",
    ),
    (
        "pyproject",
        {"old_string": "disallow_untyped_defs = true", "new_string": "disallow_untyped_defs = false"},
        True,
        "pyproject: mypy disallow_untyped_defs true -> false is caught",
    ),
    (
        "pyproject",
        {"old_string": '[tool.black]\nline-length = 88', "new_string": '[tool.black]\nline-length = 100'},
        False,
        "pyproject: an unrelated numeric setting is not caught",
    ),
    (
        "pubspec",
        {"old_string": "dependencies:", "new_string": "dependencies:\n  http: ^1.0.0"},
        False,
        "pubspec: adding a dependency is not caught (no detector for this kind)",
    ),
]


def check_detect(case) -> bool:
    kind, tool_input, expect_hit, label = case
    findings = guard.detect_loosening(kind, tool_input)
    got_hit = bool(findings)
    ok = got_hit == expect_hit
    print(f"{'PASS' if ok else 'FAIL'}: {label} (findings={findings})")
    return ok


fails += _testlib.run_cases(DETECT_CASES, check_detect)

# --- end to end: real subprocess, payload on stdin ---


def run_guard(payload_text: str):
    return subprocess.run(
        [sys.executable, str(GUARD)],
        input=payload_text, capture_output=True, text=True,
    )


def check_asked(tool_name: str, tool_input: dict, expect_ask: bool, label: str) -> bool:
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    proc = run_guard(payload)
    got_ask = "\"permissionDecision\": \"ask\"" in proc.stdout
    ok = got_ask == expect_ask and proc.returncode == 0
    print(f"[{'PASS' if ok else 'FAIL'}] {label}: ask={got_ask} rc={proc.returncode}")
    return ok


E2E_CASES = [
    (
        "Edit",
        {"file_path": "C:/proj/tsconfig.json", "old_string": '"strict": true,', "new_string": '"strict": false,'},
        True,
        "e2e: a real loosening edit (tsconfig strict->false) is caught",
    ),
    (
        "Edit",
        {"file_path": "C:/proj/tsconfig.json", "old_string": '"target": "ES2020"', "new_string": '"target": "ES2022"'},
        False,
        "e2e: an ordinary edit to the same matched file is not caught",
    ),
    (
        "Write",
        {"file_path": "C:/proj/README.md", "content": "# hello\nsome docs\n"},
        False,
        "e2e: a file outside the set is never asked about",
    ),
    (
        "MultiEdit",
        {
            "file_path": "C:/proj/.eslintrc.json",
            "edits": [
                {"old_string": '"no-console": "error"', "new_string": '"no-console": "warn"'},
            ],
        },
        True,
        "e2e: MultiEdit loosening a rule severity is caught",
    ),
    (
        "MultiEdit",
        {
            "file_path": "C:/proj/Cargo.toml",
            "edits": [
                {"old_string": "[dependencies]", "new_string": '[dependencies]\nserde = "1.0"'},
            ],
        },
        False,
        "e2e: MultiEdit adding a Cargo dependency is not caught",
    ),
]

for _tool_name, _tool_input, _expect, _label in E2E_CASES:
    if not check_asked(_tool_name, _tool_input, _expect, _label):
        fails.append(_label)


def check_write_new_file_not_asked() -> bool:
    # A path that (almost certainly) does not exist on disk: nothing prior
    # to weaken, so a brand-new file must never trigger the guard even if
    # its very first content sets strict:false.
    payload = json.dumps({
        "tool_name": "Write",
        "tool_input": {
            "file_path": "C:/this/path/does/not/exist/zz-config-loosen-guard-fixture/tsconfig.json",
            "content": '{"compilerOptions": {"strict": false}}',
        },
    })
    proc = run_guard(payload)
    ok = "ask" not in proc.stdout and proc.returncode == 0
    return _testlib.report(ok, "e2e: a brand-new file (nothing on disk to diff) is never asked about")


fails += [] if check_write_new_file_not_asked() else ["write new file not asked"]


def check_write_existing_file_loosened(tmp_path: Path) -> bool:
    cfg = tmp_path / "tsconfig.json"
    cfg.write_text('{"compilerOptions": {"strict": true}}', encoding="utf-8")
    payload = json.dumps({
        "tool_name": "Write",
        "tool_input": {
            "file_path": str(cfg),
            "content": '{"compilerOptions": {"strict": false}}',
        },
    })
    proc = run_guard(payload)
    ok = "\"permissionDecision\": \"ask\"" in proc.stdout and proc.returncode == 0
    return _testlib.report(ok, "e2e: Write over an existing on-disk file diffs against disk and catches the loosening")


import tempfile

with tempfile.TemporaryDirectory(prefix="config-loosen-guard-test-") as _tmp:
    fails += [] if check_write_existing_file_loosened(Path(_tmp)) else ["write existing file loosened"]


def check_malformed_payload() -> bool:
    proc = run_guard("not json at all {{{")
    ok = proc.returncode == 0 and "Traceback" not in proc.stderr
    return _testlib.report(ok, f"e2e: a malformed payload does not crash it (rc={proc.returncode})")


fails += [] if check_malformed_payload() else ["malformed payload crashed or exited nonzero"]


def check_empty_payload() -> bool:
    proc = run_guard("")
    ok = proc.returncode == 0 and "Traceback" not in proc.stderr
    return _testlib.report(ok, f"e2e: an empty stdin payload does not crash it (rc={proc.returncode})")


fails += [] if check_empty_payload() else ["empty payload crashed or exited nonzero"]


def check_ask_json_shape() -> bool:
    payload = json.dumps({
        "tool_name": "Edit",
        "tool_input": {"file_path": "C:/proj/tsconfig.json", "old_string": '"strict": true,', "new_string": '"strict": false,'},
    })
    proc = run_guard(payload)
    data = json.loads(proc.stdout)
    hso = data.get("hookSpecificOutput", {})
    ok = (
        hso.get("hookEventName") == "PreToolUse"
        and hso.get("permissionDecision") == "ask"
        and "headless" in hso.get("permissionDecisionReason", "")
    )
    return _testlib.report(ok, "e2e: the ask JSON shape is correct and the message names the headless escape route")


fails += [] if check_ask_json_shape() else ["ask json shape wrong or escape route missing from message"]

sys.exit(_testlib.summarize(fails, style="count"))
