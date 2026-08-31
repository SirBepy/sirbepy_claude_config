"""Self-test for todo-duplicate-guard.py (todo 363).

Run directly: python hooks/test_todo_duplicate_guard.py
Exits 0 on all-pass, 1 on any failure, printing a PASS/FAIL line per case.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_GUARD_PATH = _HOOKS_DIR / "todo-duplicate-guard.py"
guard = _testlib.load_module("todo_duplicate_guard", _GUARD_PATH)

# (file_path, expect_dir_or_None, label, windows_only)
# The two windows_only cases assert on backslash paths that are only
# path-like on Windows; on POSIX a backslash is a literal filename byte,
# so they are skipped there rather than failed (todo 454).
PATH_CASES = [
    (r"C:\Users\tecno\.claude\.claude\todos\363-x.md", True, "real double-.claude absolute path", True),
    (".claude/todos/363-x.md", True, "relative forward-slash path", False),
    (".claude\\todos\\363-x.md", True, "relative backslash path", True),
    (r"C:\Users\tecno\.claude\.claude\todos\done\307-x.md", False, "done/ subfolder is not a new-write target", False),
    (r"C:\Users\tecno\.claude\.claude\todos\.claims\363-x.claim", False, ".claims/ subfolder excluded", False),
    (r"C:\Users\tecno\.claude\.claude\todos\PLAN.md", False, "filename without digit prefix", False),
    (r"C:\Users\tecno\.claude\skills\close\ai-todos-format.md", False, "unrelated skill file", False),
    ("", False, "empty path", False),
]


def check_path(case) -> bool:
    file_path, expect_match, label, windows_only = case
    if windows_only and os.name != "nt":
        print(f"[SKIP] path: {label}: {file_path!r} (Windows-only backslash path)")
        return True
    got = guard.todos_target_dir(file_path)
    ok = (got is not None) == expect_match
    print(f"[{'PASS' if ok else 'FAIL'}] path: {label}: {file_path!r} -> {got}")
    return ok


# (title, expected tokens, label)
TOKEN_CASES = [
    ("The content-duplicate guard is documented but nothing enforces it", ["content", "duplicate", "guard", "documented", "nothing", "enforces"], "drops stopwords and short words"),
    ("Fix it", [], "all tokens too short, no signal"),
    ("Split V2 verify screen adds a third debit card form", ["split", "verify", "screen", "adds", "third", "debit", "card", "form"], "keeps identifiers, drops 'a'"),
]


def check_tokens(case) -> bool:
    title, expected, label = case
    got = guard.salient_tokens(title)
    ok = got == expected
    print(f"[{'PASS' if ok else 'FAIL'}] tokens: {label}: {title!r} -> {got}")
    return ok


# (name, expected_id_or_None, label)
ID_CASES = [
    ("492-todo-guard-checks-content.md", 492, "plain numeric prefix"),
    ("007-leading-zeros.md", 7, "leading zeros normalize"),
    ("260-.reserved", 260, "reserved marker suffix"),
    ("PLAN.md", None, "no numeric prefix"),
    ("not-a-number-x.md", None, "non-numeric prefix"),
]


def check_id(case) -> bool:
    name, expected, label = case
    got = guard.extract_id(name)
    ok = got == expected
    print(f"[{'PASS' if ok else 'FAIL'}] id: {label}: {name!r} -> {got}")
    return ok


# (tokens, matched, expect_hit, label)
HIT_CASES = [
    (["split", "verify", "screen"], ["split", "verify"], True, "2 of 3 matched, ratio >= 0.6"),
    (["split", "verify", "screen", "debit", "card"], ["split", "verify"], False, "2 of 5 matched, ratio too low and count < 3"),
    (["split", "verify", "screen", "debit", "card"], ["split", "verify", "screen"], True, "3+ matched is always a hit"),
    (["split", "verify"], ["split"], False, "only 1 matched, never a hit"),
    (["split"], [], False, "fewer than 2 salient tokens, no signal"),
]


def check_hit(case) -> bool:
    tokens, matched, expected, label = case
    got = guard.is_plausible_hit(tokens, matched)
    ok = got == expected
    print(f"[{'PASS' if ok else 'FAIL'}] hit: {label} -> {got}")
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
        done_dir = todos_dir / "done"
        done_dir.mkdir(parents=True)

        (todos_dir / "130-split-v2-verify-screen.md").write_text(
            "# Split v2 verify screen, it is too large\n\nGoal: extract the debit card form.\n",
            encoding="utf-8",
        )
        (done_dir / "88-old-declined-thing.md").write_text(
            "# Old declined thing about caching layers\n\nDeclined, not worth it.\n",
            encoding="utf-8",
        )

        new_dup_path = todos_dir / "134-v2-verify-screen-adds-a-third-debit-card-form.md"
        new_dup_content = "# v2 verify screen adds a third debit card form\n\nGoal: same as 130.\n"

        new_distinct_path = todos_dir / "200-unrelated-audio-pipeline-crash.md"
        new_distinct_content = "# Unrelated audio pipeline crash on startup\n\nGoal: fix a crash.\n"

        id_taken_path = todos_dir / "130-different-slug-entirely.md"
        id_taken_content = "# Totally different topic about zzz widgets\n\nGoal: unrelated.\n"

        id_free_path = todos_dir / "250-totally-fresh-topic-nobody-touched.md"
        id_free_content = "# Totally fresh topic nobody touched yet\n\nGoal: something new.\n"

        (todos_dir / "260-.reserved").write_text("session: test\npid: 1\n", encoding="utf-8")
        id_reserved_path = todos_dir / "260-another-fresh-topic-someone-reserved.md"
        id_reserved_content = "# Another fresh topic someone already reserved\n\nGoal: reserved.\n"

        inplace_path = todos_dir / "130-split-v2-verify-screen.md"
        inplace_content = "# Split v2 verify screen, it is too large\n\nGoal: extract the debit card form, updated.\n"

        cases = [
            (
                {"tool_name": "Write", "tool_input": {"file_path": str(new_dup_path), "content": new_dup_content}},
                2,
                "plausible duplicate of a live backlog entry is blocked",
            ),
            (
                {"tool_name": "Write", "tool_input": {"file_path": str(new_distinct_path), "content": new_distinct_content}},
                0,
                "genuinely distinct todo is allowed",
            ),
            (
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(new_dup_path),
                        "content": new_dup_content + "\n" + guard.OVERRIDE_MARKER,
                    },
                },
                0,
                "override marker in content bypasses a real hit",
            ),
            (
                {
                    "tool_name": "Write",
                    "tool_input": {
                        "file_path": str(done_dir / "999-x.md"),
                        "content": "# Split v2 verify screen debit card form\n",
                    },
                },
                0,
                "write targeting done/ itself is out of scope",
            ),
            (
                {"tool_name": "Edit", "tool_input": {"file_path": str(new_dup_path), "new_string": new_dup_content}},
                0,
                "non-Write tool is out of scope",
            ),
            (
                {"tool_name": "Write", "tool_input": {"file_path": str(id_taken_path), "content": id_taken_content}},
                2,
                "new file reusing an id already claimed by a differently-named file blocks",
            ),
            (
                {"tool_name": "Write", "tool_input": {"file_path": str(id_free_path), "content": id_free_content}},
                0,
                "new file with a free id passes",
            ),
            (
                {"tool_name": "Write", "tool_input": {"file_path": str(id_reserved_path), "content": id_reserved_content}},
                2,
                "id already claimed by a *-.reserved marker blocks",
            ),
            (
                {"tool_name": "Write", "tool_input": {"file_path": str(inplace_path), "content": inplace_content}},
                0,
                "in-place rewrite of an existing id passes",
            ),
        ]
        for payload, expect_code, label in cases:
            proc = run_hook(payload)
            ok = proc.returncode == expect_code
            print(f"[{'PASS' if ok else 'FAIL'}] integration: {label} -> exit={proc.returncode} stderr={proc.stderr.strip()!r}")
            if not ok:
                fails.append(label)

    return fails


def run() -> int:
    fails = (
        _testlib.run_cases(PATH_CASES, check_path)
        + _testlib.run_cases(TOKEN_CASES, check_tokens)
        + _testlib.run_cases(HIT_CASES, check_hit)
        + _testlib.run_cases(ID_CASES, check_id)
        + check_integration()
    )
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
