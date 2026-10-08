"""Self-test for testing-floor-flag.py and the shared helpers it uses from
_testing_floor_lib.py (todo 427).

Fully deterministic: every case runs the real hook as a subprocess, but
points TESTING_FLOOR_STATE_DIR at a private tmp directory via env var (the
injection point _testing_floor_lib.py defines) so nothing here ever touches
this checkout's real hooks/.testing-floor-pending/.

Run directly: python hooks/test_testing_floor_flag.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_HOOK_PATH = _HOOKS_DIR / "testing-floor-flag.py"
lib = _testlib.load_module("testing_floor_lib_for_flag_test", _HOOKS_DIR / "_testing_floor_lib.py")

# (path, expect_source, label)
IS_SOURCE_CASES = [
    ("src/main.py", True, "plain .py source"),
    ("hooks/testing-floor-guard.py", True, "hook code itself counts as source"),
    ("README.md", False, ".md excluded"),
    ("CLAUDE.md", False, ".md excluded, repo-root file"),
    ("package.json", False, ".json excluded (config-shaped)"),
    ("Cargo.toml", False, ".toml excluded (config-shaped)"),
    (".claude/todos/427-thing.md", False, "todos dir segment excluded"),
    ("skills/commit/SKILL.md", False, "skills dir segment excluded (and .md)"),
    ("skills/commit/commit-pathspec.sh", False, "skills dir segment excludes even a .sh"),
    ("refs/process-hygiene.md", False, "refs dir segment excluded"),
    ("lib/widget.dart", True, "flutter source"),
    ("src/app.rs", True, "rust source"),
    ("node_modules/pkg/index.js", False, "node_modules excluded despite .js"),
    ("notes.txt", False, "unrecognised/config-shaped extension defaults OFF"),
    ("data/schema.unknownext", False, "unknown extension defaults OFF (allowlist bias)"),
    ("windows\\style\\path\\main.py", True, "windows-style backslash path, source"),
    ("windows\\style\\.claude\\todos\\1-x.md", False, "windows-style backslash path, todos segment"),
]


def check_is_source(case) -> bool:
    path, expect, label = case
    got = lib.is_source_file(path)
    ok = got == expect
    print(f"[{'PASS' if ok else 'FAIL'}] is_source_file: {label}: {path!r} -> {got}")
    return ok


def run_hook(payload: dict, state_dir: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["TESTING_FLOOR_STATE_DIR"] = str(state_dir)
    return subprocess.run(
        [sys.executable, str(_HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def integration_checks() -> list:
    fails = []
    with tempfile.TemporaryDirectory(prefix="testing-floor-flag-test-") as tmp:
        tmp_path = Path(tmp)

        # Case 1: source-file Write, real session -> flag file created, attempts=0.
        state_dir = tmp_path / "state1"
        session_id = "sess-source-write"
        payload = {
            "session_id": session_id,
            "cwd": str(tmp_path),
            "tool_name": "Write",
            "tool_input": {"file_path": str(tmp_path / "src" / "app.py"), "content": "x"},
        }
        proc = run_hook(payload, state_dir)
        flag_path = state_dir / session_id
        ok = proc.returncode == 0 and flag_path.is_file()
        if ok:
            state = json.loads(flag_path.read_text(encoding="utf-8"))
            ok = state.get("attempts") == 0 and "root" in state
        print(f"[{'PASS' if ok else 'FAIL'}] integration: source-file Write creates flag with attempts=0 -> exit={proc.returncode} exists={flag_path.is_file()}")
        if not ok:
            fails.append("source-file Write creates flag")

        # Case 2: non-source (.md) Write, same session dir -> no flag file.
        state_dir2 = tmp_path / "state2"
        session_id2 = "sess-md-write"
        payload2 = {
            "session_id": session_id2,
            "cwd": str(tmp_path),
            "tool_name": "Write",
            "tool_input": {"file_path": str(tmp_path / "NOTES.md"), "content": "x"},
        }
        proc2 = run_hook(payload2, state_dir2)
        flag_path2 = state_dir2 / session_id2
        ok2 = proc2.returncode == 0 and not flag_path2.exists()
        print(f"[{'PASS' if ok2 else 'FAIL'}] integration: .md Write does not create a flag -> exit={proc2.returncode} exists={flag_path2.exists()}")
        if not ok2:
            fails.append(".md Write does not create a flag")

        # Case 3: agent_id present on an otherwise-qualifying source Write -> no flag.
        state_dir3 = tmp_path / "state3"
        session_id3 = "sess-agent"
        payload3 = {
            "session_id": session_id3,
            "cwd": str(tmp_path),
            "agent_id": "aaaeae68dcacc2c9d",
            "agent_type": "general-purpose",
            "tool_name": "Write",
            "tool_input": {"file_path": str(tmp_path / "src" / "app.py"), "content": "x"},
        }
        proc3 = run_hook(payload3, state_dir3)
        flag_path3 = state_dir3 / session_id3
        ok3 = proc3.returncode == 0 and not flag_path3.exists()
        print(f"[{'PASS' if ok3 else 'FAIL'}] integration: subagent source-file Write does not create a flag -> exit={proc3.returncode} exists={flag_path3.exists()}")
        if not ok3:
            fails.append("subagent Write does not create a flag")

        # Case 4: non-edit tool (Read) on a source file -> no flag.
        state_dir4 = tmp_path / "state4"
        session_id4 = "sess-read"
        payload4 = {
            "session_id": session_id4,
            "cwd": str(tmp_path),
            "tool_name": "Read",
            "tool_input": {"file_path": str(tmp_path / "src" / "app.py")},
        }
        proc4 = run_hook(payload4, state_dir4)
        flag_path4 = state_dir4 / session_id4
        ok4 = proc4.returncode == 0 and not flag_path4.exists()
        print(f"[{'PASS' if ok4 else 'FAIL'}] integration: Read (non-edit tool) does not create a flag -> exit={proc4.returncode} exists={flag_path4.exists()}")
        if not ok4:
            fails.append("Read does not create a flag")

        # Case 5: missing session_id -> no flag anywhere, no crash.
        state_dir5 = tmp_path / "state5"
        payload5 = {
            "cwd": str(tmp_path),
            "tool_name": "Write",
            "tool_input": {"file_path": str(tmp_path / "src" / "app.py"), "content": "x"},
        }
        proc5 = run_hook(payload5, state_dir5)
        ok5 = proc5.returncode == 0 and (not state_dir5.exists() or not any(state_dir5.iterdir()))
        print(f"[{'PASS' if ok5 else 'FAIL'}] integration: missing session_id does not crash or write anything -> exit={proc5.returncode}")
        if not ok5:
            fails.append("missing session_id safe")

        # Case 6: a stale flag (attempts=5, leftover from a prior failing
        # cycle) gets RESET to attempts=0 by a fresh source edit - a new fix
        # attempt must not inherit the old retry budget.
        state_dir6 = tmp_path / "state6"
        session_id6 = "sess-reset"
        flag_path6 = state_dir6 / session_id6
        flag_path6.parent.mkdir(parents=True)
        flag_path6.write_text(json.dumps({"attempts": 5, "root": "stale"}), encoding="utf-8")
        payload6 = {
            "session_id": session_id6,
            "cwd": str(tmp_path),
            "tool_name": "Edit",
            "tool_input": {"file_path": str(tmp_path / "src" / "app.py"), "new_string": "x"},
        }
        proc6 = run_hook(payload6, state_dir6)
        ok6 = proc6.returncode == 0 and flag_path6.is_file()
        if ok6:
            state6 = json.loads(flag_path6.read_text(encoding="utf-8"))
            ok6 = state6.get("attempts") == 0
        print(f"[{'PASS' if ok6 else 'FAIL'}] integration: a fresh edit resets a stale attempts counter to 0 -> exit={proc6.returncode}")
        if not ok6:
            fails.append("fresh edit resets stale attempts")

        # Case 8: two source-file edits in the SAME
        # session accumulate into state["paths"] rather than the second
        # overwriting the first - this is what lets the scripts-repo row
        # target every file this turn touched, not just the latest one.
        state_dir8 = tmp_path / "state8"
        session_id8 = "sess-accumulate"
        path_a = str(tmp_path / "src" / "a.py")
        path_b = str(tmp_path / "src" / "b.py")
        proc8a = run_hook(
            {"session_id": session_id8, "cwd": str(tmp_path), "tool_name": "Write",
             "tool_input": {"file_path": path_a, "content": "x"}},
            state_dir8,
        )
        proc8b = run_hook(
            {"session_id": session_id8, "cwd": str(tmp_path), "tool_name": "Write",
             "tool_input": {"file_path": path_b, "content": "x"}},
            state_dir8,
        )
        flag_path8 = state_dir8 / session_id8
        ok8 = proc8a.returncode == 0 and proc8b.returncode == 0 and flag_path8.is_file()
        paths8 = None
        if ok8:
            state8 = json.loads(flag_path8.read_text(encoding="utf-8"))
            paths8 = state8.get("paths")
            ok8 = paths8 == [path_a, path_b] and state8.get("attempts") == 0
        print(f"[{'PASS' if ok8 else 'FAIL'}] integration: two edits in one session accumulate both paths -> paths={paths8!r}")
        if not ok8:
            fails.append("two edits accumulate both paths")

        # Case 9: editing the SAME path twice dedupes rather than growing.
        state_dir9 = tmp_path / "state9"
        session_id9 = "sess-dedupe"
        path_c = str(tmp_path / "src" / "c.py")
        run_hook(
            {"session_id": session_id9, "cwd": str(tmp_path), "tool_name": "Edit",
             "tool_input": {"file_path": path_c, "new_string": "x"}},
            state_dir9,
        )
        proc9b = run_hook(
            {"session_id": session_id9, "cwd": str(tmp_path), "tool_name": "Edit",
             "tool_input": {"file_path": path_c, "new_string": "y"}},
            state_dir9,
        )
        flag_path9 = state_dir9 / session_id9
        ok9 = proc9b.returncode == 0 and flag_path9.is_file()
        paths9 = None
        if ok9:
            state9 = json.loads(flag_path9.read_text(encoding="utf-8"))
            paths9 = state9.get("paths")
            ok9 = paths9 == [path_c]
        print(f"[{'PASS' if ok9 else 'FAIL'}] integration: editing the same path twice dedupes -> paths={paths9!r}")
        if not ok9:
            fails.append("same path edited twice dedupes")

        # Case 10: an edit in a second repo restarts the path list, since the
        # gate checks one root and a foreign path would py_compile against it.
        state_dir10 = tmp_path / "state10"
        session_id10 = "sess-two-repos"
        repo_one, repo_two = tmp_path / "repo-one", tmp_path / "repo-two"
        path_one, path_two = str(repo_one / "a.py"), str(repo_two / "b.py")
        for cwd, path in ((repo_one, path_one), (repo_two, path_two)):
            run_hook(
                {"session_id": session_id10, "cwd": str(cwd), "tool_name": "Write",
                 "tool_input": {"file_path": path, "content": "x"}},
                state_dir10,
            )
        state10 = json.loads((state_dir10 / session_id10).read_text(encoding="utf-8"))
        ok10 = state10.get("paths") == [path_two] and Path(state10.get("root")) == repo_two
        print(f"[{'PASS' if ok10 else 'FAIL'}] integration: a second repo restarts the path list -> {state10!r}")
        if not ok10:
            fails.append("a second repo restarts the path list")

        # Case 7: malformed stdin -> exits 0, does not crash.
        proc7 = subprocess.run(
            [sys.executable, str(_HOOK_PATH)],
            input="not valid json {{{",
            capture_output=True,
            text=True,
        )
        ok7 = proc7.returncode == 0
        print(f"[{'PASS' if ok7 else 'FAIL'}] integration: malformed stdin still exits 0 -> exit={proc7.returncode} stderr={proc7.stderr.strip()!r}")
        if not ok7:
            fails.append("malformed stdin exits 0")

    return fails


def run() -> int:
    fails = _testlib.run_cases(IS_SOURCE_CASES, check_is_source) + integration_checks()
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
