"""Self-test for todos-em-dash-guard.py (todo 318).

Run directly: python hooks/test_todos_em_dash_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "todos-em-dash-guard.py"
guard = _testlib.load_module("todos_em_dash_guard", _GUARD_PATH)

ED = chr(0x2014)

# (file_path, expect_todos_path, label)
PATH_CASES = [
    (r"C:\Users\tecno\.claude\.claude\todos\318-x.md", True, "real double-.claude absolute path"),
    (".claude/todos/318-x.md", True, "relative forward-slash path"),
    (".claude\\todos\\318-x.md", True, "relative backslash path"),
    (r"C:\Users\tecno\.claude\.claude\todos\done\307-x.md", True, "done/ subfolder still in scope"),
    (r"C:\Users\tecno\.claude\skills\commit\em-dash.sh", False, "unrelated skill file"),
    (r"C:\Users\tecno\myclaude\todos-backup\x.md", False, "lookalike folder name, not a real segment match"),
    ("", False, "empty path"),
]


def check_path(case) -> bool:
    file_path, expect, label = case
    got = guard.is_todos_path(file_path)
    ok = got == expect
    print(f"[{'PASS' if ok else 'FAIL'}] path: {label}: {file_path!r} -> {got}")
    return ok


# (text, expect_block, label)
DASH_CASES = [
    ("Here is a plain summary with no violations.", False, "clean prose"),
    ("", False, "empty string"),
    (f"Two options{ED} pick one.", True, "literal em dash"),
    ("plain hyphen - and en dash \u2013 are fine", False, "sibling dash characters not flagged"),
]


def check_dash(case) -> bool:
    text, expect_block, label = case
    got_block = guard.find_em_dash(text) != -1
    ok = got_block == expect_block
    print(f"[{'PASS' if ok else 'FAIL'}] dash: {label}: {text!r} -> {'BLOCK' if got_block else 'PASS'}")
    return ok


# (tool_name, tool_input, expected joined content, label)
CONTENT_CASES = [
    ("Write", {"content": "hello"}, "hello", "Write uses content"),
    ("Edit", {"new_string": "hello"}, "hello", "Edit uses new_string"),
    (
        "MultiEdit",
        {"edits": [{"new_string": "a"}, {"new_string": "b"}]},
        "a\nb",
        "MultiEdit joins each edit's new_string",
    ),
    ("Read", {"file_path": "x"}, "", "unrelated tool yields nothing"),
]


def check_content(case) -> bool:
    tool_name, tool_input, expected, label = case
    got = "\n".join(guard.new_content_strings(tool_name, tool_input))
    ok = got == expected
    print(f"[{'PASS' if ok else 'FAIL'}] content: {label}: -> {got!r}")
    return ok


def run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_GUARD_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


def check_integration() -> list:
    fails = []
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        todos_dir = tmpdir / ".claude" / "todos"
        todos_dir.mkdir(parents=True)
        other_dir = tmpdir / ".claude" / "skills"
        other_dir.mkdir(parents=True)

        target = todos_dir / "999-x.md"
        outside = other_dir / "999-x.md"

        cases = [
            (
                {"tool_name": "Write", "tool_input": {"file_path": str(target), "content": f"bad{ED}text"}},
                2,
                "Write with em dash under .claude/todos/ is blocked",
            ),
            (
                {"tool_name": "Write", "tool_input": {"file_path": str(outside), "content": f"bad{ED}text"}},
                0,
                "same content outside .claude/todos/ is allowed",
            ),
            (
                {"tool_name": "Write", "tool_input": {"file_path": str(target), "content": "clean text"}},
                0,
                "Write with no em dash is allowed",
            ),
            (
                {"tool_name": "Edit", "tool_input": {"file_path": str(target), "old_string": "a", "new_string": f"bad{ED}text"}},
                2,
                "Edit new_string with em dash is blocked",
            ),
            (
                {
                    "tool_name": "MultiEdit",
                    "tool_input": {"file_path": str(target), "edits": [{"old_string": "a", "new_string": "clean"}, {"old_string": "b", "new_string": f"bad{ED}"}]},
                },
                2,
                "MultiEdit with em dash in any edit is blocked",
            ),
            (
                {"tool_name": "Write", "tool_input": {"file_path": str(target), "content": f"bad{ED}text {guard.EXEMPT_MARKER}"}},
                0,
                "exemption marker in the new content allows the write",
            ),
        ]
        for payload, expect_code, label in cases:
            proc = run_hook(payload)
            ok = proc.returncode == expect_code
            print(f"[{'PASS' if ok else 'FAIL'}] integration: {label} -> exit={proc.returncode} stderr={proc.stderr.strip()!r}")
            if not ok:
                fails.append(label)

        # Marker already on disk (from a prior Write) exempts a later Edit
        # that doesn't restate it.
        target.write_text(f"{guard.EXEMPT_MARKER}\nsome{ED}text", encoding="utf-8")
        proc = run_hook(
            {"tool_name": "Edit", "tool_input": {"file_path": str(target), "old_string": "some", "new_string": f"more{ED}text"}}
        )
        label = "marker already on disk exempts a later Edit"
        ok = proc.returncode == 0
        print(f"[{'PASS' if ok else 'FAIL'}] integration: {label} -> exit={proc.returncode} stderr={proc.stderr.strip()!r}")
        if not ok:
            fails.append(label)

    return fails


def run() -> int:
    fails = (
        _testlib.run_cases(PATH_CASES, check_path)
        + _testlib.run_cases(DASH_CASES, check_dash)
        + _testlib.run_cases(CONTENT_CASES, check_content)
        + check_integration()
    )
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
