"""Self-test for testing-floor-guard.py and its evaluate() core (todo 427).

Two layers, matching this repo's established convention (see
test_ui_screenshot_reminder.py / test_agent_todo_write_guard.py):

1. In-process unit tests calling `evaluate()` directly with injected
   dependencies (tmp state dir, tmp skip-flag path, a fake run_checks_fn) -
   covers escape hatch, activation gate, subagent exclusion, and the retry
   cap without ever touching a real subprocess or this repo's real state.
2. Subprocess integration tests of the real hook entry point, using the
   TESTING_FLOOR_* env-var injection points _testing_floor_lib.py defines,
   including one true "deliberately-broken project" case and one true
   "genuinely passing project" case that exercise the REAL detect_stack +
   subprocess path (a tiny fake ci/run_all.py, not a stubbed result) - the
   todo's own instruction that a gate only tested on the happy path is
   untested.

Nothing here depends on this checkout's real hooks/.testing-floor-pending/,
hooks/.testing-floor-skip, or ci/run_all.py.

Run directly: python hooks/test_testing_floor_guard.py
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

import _testlib

_HOOKS_DIR = Path(__file__).resolve().parent
_HOOK_PATH = _HOOKS_DIR / "testing-floor-guard.py"
guard = _testlib.load_module("testing_floor_guard", _HOOK_PATH)

AGENT_PAYLOAD = {"session_id": "s1", "agent_id": "aaaeae68dcacc2c9d", "agent_type": "general-purpose"}
ORCHESTRATOR_PAYLOAD = {"session_id": "s1"}


def fake_run_checks(result):
    """Builds a run_checks_fn stub: result is True (pass), False (fail), or
    the string "raise" (fault injection for the fail-open path). Accepts
    **kwargs so it tolerates evaluate()'s `paths=` forwarding (todo 427
    defect 1) without every call site needing to know about it."""
    def _fn(root, **kwargs):
        if result == "raise":
            raise RuntimeError("stubbed failure")
        return (result, "stubbed summary")
    return _fn


def unit_checks() -> list:
    fails = []

    def case(label, payload, state_dir, skip_flag_path, cap, run_checks_fn, expect_block):
        got = guard.evaluate(
            payload,
            state_dir=state_dir,
            skip_flag_path=skip_flag_path,
            cap=cap,
            run_checks_fn=run_checks_fn,
            env={},
        )
        ok = (got is not None) == expect_block
        print(f"[{'PASS' if ok else 'FAIL'}] unit: {label} -> {got!r}")
        if not ok:
            fails.append(label)
        return got

    with tempfile.TemporaryDirectory(prefix="testing-floor-guard-unit-") as tmp:
        tmp_path = Path(tmp)

        # Subagent exclusion: never blocks, regardless of state on disk.
        case(
            "subagent call never blocks even with a pending flag",
            AGENT_PAYLOAD,
            tmp_path / "state-a", tmp_path / "skip-a", 3,
            fake_run_checks(False),
            expect_block=False,
        )

        # Activation gate: no flag file for this session -> no-op regardless
        # of what run_checks_fn would have said.
        case(
            "no pending flag -> no-op even though checks would fail",
            ORCHESTRATOR_PAYLOAD,
            tmp_path / "state-b", tmp_path / "skip-b", 3,
            fake_run_checks(False),
            expect_block=False,
        )

        # Missing session_id -> no-op.
        case(
            "missing session_id -> no-op",
            {},
            tmp_path / "state-c", tmp_path / "skip-c", 3,
            fake_run_checks(False),
            expect_block=False,
        )

        # Pending flag + failing checks -> blocks, and attempts increments.
        state_dir_d = tmp_path / "state-d"
        flag_d = state_dir_d / "s1"
        state_dir_d.mkdir(parents=True)
        flag_d.write_text(json.dumps({"attempts": 0, "root": "."}), encoding="utf-8")
        result_d = case(
            "pending flag + failing checks -> blocks",
            ORCHESTRATOR_PAYLOAD,
            state_dir_d, tmp_path / "skip-d", 3,
            fake_run_checks(False),
            expect_block=True,
        )
        ok = result_d is not None and result_d.get("decision") == "block" and "1/3" in result_d.get("reason", "")
        print(f"[{'PASS' if ok else 'FAIL'}] unit: block reason names attempt 1/3 -> {result_d!r}")
        if not ok:
            fails.append("block reason names attempt count")
        state_after_d = json.loads(flag_d.read_text(encoding="utf-8"))
        ok = state_after_d.get("attempts") == 1
        print(f"[{'PASS' if ok else 'FAIL'}] unit: attempts persisted as 1 after first block -> {state_after_d!r}")
        if not ok:
            fails.append("attempts persisted after first block")

        # Pending flag + passing checks -> allows AND clears the flag file.
        state_dir_e = tmp_path / "state-e"
        flag_e = state_dir_e / "s1"
        state_dir_e.mkdir(parents=True)
        flag_e.write_text(json.dumps({"attempts": 2, "root": "."}), encoding="utf-8")
        case(
            "pending flag + passing checks -> allows",
            ORCHESTRATOR_PAYLOAD,
            state_dir_e, tmp_path / "skip-e", 3,
            fake_run_checks(True),
            expect_block=False,
        )
        ok = not flag_e.exists()
        print(f"[{'PASS' if ok else 'FAIL'}] unit: passing checks clear the flag file -> exists={flag_e.exists()}")
        if not ok:
            fails.append("passing checks clear the flag")

        # Escape hatch via env: blocks would otherwise fire, env wins.
        state_dir_f = tmp_path / "state-f"
        flag_f = state_dir_f / "s1"
        state_dir_f.mkdir(parents=True)
        flag_f.write_text(json.dumps({"attempts": 0, "root": "."}), encoding="utf-8")
        got_f = guard.evaluate(
            ORCHESTRATOR_PAYLOAD,
            state_dir=state_dir_f, skip_flag_path=tmp_path / "skip-f", cap=3,
            run_checks_fn=fake_run_checks(False),
            env={"CLAUDE_TESTING_FLOOR_SKIP": "1"},
        )
        ok = got_f is None
        print(f"[{'PASS' if ok else 'FAIL'}] unit: escape-hatch env var overrides a failing check -> {got_f!r}")
        if not ok:
            fails.append("escape hatch env var wins")

        # Escape hatch via flag file: same, no env needed.
        state_dir_g = tmp_path / "state-g"
        flag_g = state_dir_g / "s1"
        state_dir_g.mkdir(parents=True)
        flag_g.write_text(json.dumps({"attempts": 0, "root": "."}), encoding="utf-8")
        skip_path_g = tmp_path / "skip-g"
        skip_path_g.write_text("x", encoding="utf-8")
        got_g = guard.evaluate(
            ORCHESTRATOR_PAYLOAD,
            state_dir=state_dir_g, skip_flag_path=skip_path_g, cap=3,
            run_checks_fn=fake_run_checks(False),
            env={},
        )
        ok = got_g is None
        print(f"[{'PASS' if ok else 'FAIL'}] unit: escape-hatch flag FILE overrides a failing check -> {got_g!r}")
        if not ok:
            fails.append("escape hatch flag file wins")

        # Retry cap: attempts already AT cap -> releases without even
        # calling run_checks_fn (proven by a stub that would raise if called).
        state_dir_h = tmp_path / "state-h"
        flag_h = state_dir_h / "s1"
        state_dir_h.mkdir(parents=True)
        flag_h.write_text(json.dumps({"attempts": 3, "root": "."}), encoding="utf-8")

        def must_not_be_called(root):
            raise AssertionError("run_checks_fn must not be called once the cap is already spent")

        got_h = guard.evaluate(
            ORCHESTRATOR_PAYLOAD,
            state_dir=state_dir_h, skip_flag_path=tmp_path / "skip-h", cap=3,
            run_checks_fn=must_not_be_called,
            env={},
        )
        ok = got_h is None and not flag_h.exists()
        print(f"[{'PASS' if ok else 'FAIL'}] unit: attempts already at cap releases without rerunning checks -> {got_h!r} exists={flag_h.exists()}")
        if not ok:
            fails.append("cap releases without rerunning")

        # Loop-bound simulation: repeatedly failing checks with NO further
        # edits (attempts counter never reset) must stop blocking exactly at
        # the cap - "a deliberately unfixable failure terminates at the cap
        # instead of looping" (todo's own acceptance line).
        state_dir_i = tmp_path / "state-i"
        flag_i = state_dir_i / "s1"
        state_dir_i.mkdir(parents=True)
        flag_i.write_text(json.dumps({"attempts": 0, "root": "."}), encoding="utf-8")
        cap_i = 3
        blocked_count = 0
        for round_num in range(1, 10):
            got_i = guard.evaluate(
                ORCHESTRATOR_PAYLOAD,
                state_dir=state_dir_i, skip_flag_path=tmp_path / "skip-i", cap=cap_i,
                run_checks_fn=fake_run_checks(False),
                env={},
            )
            if got_i is not None:
                blocked_count += 1
            elif round_num > 1:
                break  # released - loop is over
        ok = blocked_count == cap_i
        print(f"[{'PASS' if ok else 'FAIL'}] unit: a permanently-failing project blocks exactly {cap_i} times then releases -> blocked {blocked_count} times")
        if not ok:
            fails.append("permanently-failing project stops at cap")

        # Fail-open: run_checks_fn raises -> evaluate() must propagate (not
        # swallow) so main()'s own top-level try/except is what fails open -
        # proven separately below via the real subprocess entry point, this
        # unit case just documents evaluate() does NOT itself catch it.
        state_dir_j = tmp_path / "state-j"
        flag_j = state_dir_j / "s1"
        state_dir_j.mkdir(parents=True)
        flag_j.write_text(json.dumps({"attempts": 0, "root": "."}), encoding="utf-8")
        raised = False
        try:
            guard.evaluate(
                ORCHESTRATOR_PAYLOAD,
                state_dir=state_dir_j, skip_flag_path=tmp_path / "skip-j", cap=3,
                run_checks_fn=fake_run_checks("raise"),
                env={},
            )
        except RuntimeError:
            raised = True
        print(f"[{'PASS' if raised else 'FAIL'}] unit: evaluate() propagates a run_checks_fn exception (main() is the fail-open boundary) -> raised={raised}")
        if not raised:
            fails.append("evaluate propagates run_checks_fn exception")

    return fails


def run_hook(payload: dict, extra_env: dict) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(_HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
    )


def subprocess_checks() -> list:
    fails = []
    with tempfile.TemporaryDirectory(prefix="testing-floor-guard-subprocess-") as tmp:
        tmp_path = Path(tmp)

        # Stubbed pass via TESTING_FLOOR_FAKE_CHECK: pending flag, real
        # subprocess entry point, no real project on disk.
        state_dir = tmp_path / "state-pass"
        session_id = "sess-pass"
        flag_path = state_dir / session_id
        state_dir.mkdir(parents=True)
        flag_path.write_text(json.dumps({"attempts": 0, "root": "."}), encoding="utf-8")
        proc = run_hook(
            {"session_id": session_id},
            {"TESTING_FLOOR_STATE_DIR": str(state_dir), "TESTING_FLOOR_FAKE_CHECK": "pass"},
        )
        ok = proc.returncode == 0 and proc.stdout.strip() == "" and not flag_path.exists()
        print(f"[{'PASS' if ok else 'FAIL'}] subprocess: stubbed pass allows and clears flag -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not ok:
            fails.append("subprocess stubbed pass")

        # Stubbed fail -> blocks with structured JSON on stdout.
        state_dir2 = tmp_path / "state-fail"
        session_id2 = "sess-fail"
        flag_path2 = state_dir2 / session_id2
        state_dir2.mkdir(parents=True)
        flag_path2.write_text(json.dumps({"attempts": 0, "root": "."}), encoding="utf-8")
        proc2 = run_hook(
            {"session_id": session_id2},
            {"TESTING_FLOOR_STATE_DIR": str(state_dir2), "TESTING_FLOOR_FAKE_CHECK": "fail"},
        )
        ok2 = proc2.returncode == 0 and '"decision": "block"' in proc2.stdout and flag_path2.exists()
        print(f"[{'PASS' if ok2 else 'FAIL'}] subprocess: stubbed fail blocks via decision:block JSON -> exit={proc2.returncode} stdout={proc2.stdout.strip()!r}")
        if not ok2:
            fails.append("subprocess stubbed fail")

        # Fault injection (run_checks itself raises) -> hook still exits 0
        # (main()'s top-level try/except is the real fail-open boundary).
        state_dir3 = tmp_path / "state-raise"
        session_id3 = "sess-raise"
        flag_path3 = state_dir3 / session_id3
        state_dir3.mkdir(parents=True)
        flag_path3.write_text(json.dumps({"attempts": 0, "root": "."}), encoding="utf-8")
        proc3 = run_hook(
            {"session_id": session_id3},
            {"TESTING_FLOOR_STATE_DIR": str(state_dir3), "TESTING_FLOOR_FAKE_CHECK": "raise"},
        )
        ok3 = proc3.returncode == 0
        print(f"[{'PASS' if ok3 else 'FAIL'}] subprocess: run_checks raising still exits 0 (fail-open) -> exit={proc3.returncode} stderr={proc3.stderr.strip()!r}")
        if not ok3:
            fails.append("subprocess fail-open on raise")

        # Malformed stdin -> exits 0.
        proc4 = subprocess.run(
            [sys.executable, str(_HOOK_PATH)],
            input="not valid json {{{",
            capture_output=True,
            text=True,
        )
        ok4 = proc4.returncode == 0
        print(f"[{'PASS' if ok4 else 'FAIL'}] subprocess: malformed stdin still exits 0 -> exit={proc4.returncode} stderr={proc4.stderr.strip()!r}")
        if not ok4:
            fails.append("subprocess malformed stdin")

        # Subagent payload -> allows even with a failing stub and a pending flag.
        state_dir5 = tmp_path / "state-agent"
        session_id5 = "s1"
        flag_path5 = state_dir5 / session_id5
        state_dir5.mkdir(parents=True)
        flag_path5.write_text(json.dumps({"attempts": 0, "root": "."}), encoding="utf-8")
        proc5 = run_hook(
            {**AGENT_PAYLOAD, "session_id": session_id5},
            {"TESTING_FLOOR_STATE_DIR": str(state_dir5), "TESTING_FLOOR_FAKE_CHECK": "fail"},
        )
        ok5 = proc5.returncode == 0 and proc5.stdout.strip() == ""
        print(f"[{'PASS' if ok5 else 'FAIL'}] subprocess: subagent payload never blocks even on a failing stub -> exit={proc5.returncode} stdout={proc5.stdout.strip()!r}")
        if not ok5:
            fails.append("subprocess subagent never blocks")

    return fails


def real_detection_checks() -> list:
    """Exercises the REAL detect_stack + subprocess path (no
    TESTING_FLOOR_FAKE_CHECK stub) against a scripts-repo project - the
    todo's own instruction that the gate must be proven against a
    deliberately-broken case, not just a stubbed one.

    Rewritten for todo 427 defect 1: every `ci/run_all.py` here is a marker
    file only, deliberately made to FAIL if it were ever executed
    ("SHOULD NEVER RUN" + exit 1) - the real verdict must come from the
    targeted py_compile/self-test commands built from `paths`, never from
    running the full suite. A case with no "paths" key at all (an old
    state file predating this fix) must still pass even with that
    always-fails marker present, proving there is no fallback to the full
    suite.
    """
    fails = []
    with tempfile.TemporaryDirectory(prefix="testing-floor-guard-real-") as tmp:
        tmp_path = Path(tmp)

        def make_root(name: str) -> Path:
            root = tmp_path / name
            (root / "ci").mkdir(parents=True)
            (root / "ci" / "run_all.py").write_text(
                textwrap.dedent("""
                    import sys
                    print("SHOULD NEVER RUN: the full suite must never execute from this hook")
                    sys.exit(1)
                """).strip() + "\n",
                encoding="utf-8",
            )
            (root / "hooks").mkdir()
            return root

        # A deliberately-broken edited file: real py_compile on a syntax
        # error genuinely fails.
        broken_root = make_root("broken-project")
        bad_py = broken_root / "hooks" / "bad.py"
        bad_py.write_text("def f(:\n", encoding="utf-8")
        state_dir_broken = tmp_path / "state-broken"
        session_broken = "sess-broken"
        flag_broken = state_dir_broken / session_broken
        state_dir_broken.mkdir(parents=True)
        flag_broken.write_text(
            json.dumps({"attempts": 0, "root": str(broken_root), "paths": [str(bad_py)]}),
            encoding="utf-8",
        )
        proc = run_hook({"session_id": session_broken}, {"TESTING_FLOOR_STATE_DIR": str(state_dir_broken)})
        ok = (
            proc.returncode == 0
            and '"decision": "block"' in proc.stdout
            and "py_compile" in proc.stdout
            and "SHOULD NEVER RUN" not in proc.stdout
        )
        print(f"[{'PASS' if ok else 'FAIL'}] real-detection: a real py_compile syntax error blocks the turn, full suite never runs -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not ok:
            fails.append("real detection: py_compile failure blocks, full suite never runs")

        # A genuinely valid edited file: real py_compile succeeds.
        passing_root = make_root("passing-project")
        good_py = passing_root / "hooks" / "good.py"
        good_py.write_text("x = 1\n", encoding="utf-8")
        state_dir_pass = tmp_path / "state-real-pass"
        session_pass = "sess-real-pass"
        flag_pass = state_dir_pass / session_pass
        state_dir_pass.mkdir(parents=True)
        flag_pass.write_text(
            json.dumps({"attempts": 0, "root": str(passing_root), "paths": [str(good_py)]}),
            encoding="utf-8",
        )
        proc2 = run_hook({"session_id": session_pass}, {"TESTING_FLOOR_STATE_DIR": str(state_dir_pass)})
        ok2 = proc2.returncode == 0 and proc2.stdout.strip() == "" and not flag_pass.exists()
        print(f"[{'PASS' if ok2 else 'FAIL'}] real-detection: a valid edited .py allows the turn and clears the flag, full suite never runs -> exit={proc2.returncode} stdout={proc2.stdout.strip()!r}")
        if not ok2:
            fails.append("real detection: passing py_compile case allows")

        # An old state file with no "paths" key at all (predates this fix):
        # the scripts-repo row has nothing targeted, so it passes even
        # though its ci/run_all.py marker would fail if it ever ran.
        nopaths_root = make_root("nopaths-project")
        state_dir_nopaths = tmp_path / "state-nopaths"
        session_nopaths = "sess-nopaths"
        flag_nopaths = state_dir_nopaths / session_nopaths
        state_dir_nopaths.mkdir(parents=True)
        flag_nopaths.write_text(json.dumps({"attempts": 0, "root": str(nopaths_root)}), encoding="utf-8")
        proc3 = run_hook({"session_id": session_nopaths}, {"TESTING_FLOOR_STATE_DIR": str(state_dir_nopaths)})
        ok3 = proc3.returncode == 0 and proc3.stdout.strip() == "" and not flag_nopaths.exists()
        print(f"[{'PASS' if ok3 else 'FAIL'}] real-detection: old state file with no \"paths\" key passes, never falls back to the full suite -> exit={proc3.returncode} stdout={proc3.stdout.strip()!r}")
        if not ok3:
            fails.append("real detection: no-paths state falls back to pass, not the full suite")

    return fails


def dual_stack_checks() -> list:
    """Regression for todo 427 Notes item 4: `detect_stack()` returned a
    single `(label, argv)` tuple and stopped at the first marker-file hit
    in a fixed priority order, so a dual-stack repo (the exact Tauri shape
    `skills/test/SKILL.md` names: Cargo.toml + package.json) only ever got
    ONE stack's checks run, though the module docstring claimed parity with
    that SKILL.md's "run every row it matches" rule. Reproduced with a
    scratch dir holding both markers and a fake `runner` that returns a
    DIFFERENT, distinguishable result per stack (rust passes, node fails),
    so the test can tell whether both actually ran or only one did.
    """
    fails = []
    lib = _testlib.load_module("testing_floor_lib", _HOOKS_DIR / "_testing_floor_lib.py")

    with tempfile.TemporaryDirectory(prefix="testing-floor-dual-stack-") as tmp:
        root = Path(tmp)
        (root / "Cargo.toml").write_text('[package]\nname = "x"\n', encoding="utf-8")
        # A real scripts.test entry - an empty/placeholder one would (correctly)
        # be excluded by the node-row check below, which would defeat this
        # test's actual purpose of proving BOTH stacks get checked.
        (root / "package.json").write_text(json.dumps({"scripts": {"test": "vitest run"}}), encoding="utf-8")

        stacks = lib.detect_stack(root)
        labels = [label for label, _argv in stacks]
        ok = set(labels) == {"rust", "node"}
        print(f"[{'PASS' if ok else 'FAIL'}] lib: detect_stack names BOTH rust and node for a Cargo.toml+package.json repo -> {stacks!r}")
        if not ok:
            fails.append("detect_stack returns both matches for a dual-stack repo")

        class FakeProc:
            def __init__(self, returncode, stdout):
                self.returncode = returncode
                self.stdout = stdout
                self.stderr = ""

        def fake_runner(argv, **kwargs):
            # rust passes, node fails - distinguishable per-stack outcomes
            # so a joined summary/ok that ignored one stack is detectable.
            if argv[0] == "cargo":
                return FakeProc(0, "RUST-MARKER: cargo test passed")
            return FakeProc(1, "NODE-MARKER: npm test failed")

        ok_all, summary = lib.run_checks(root, runner=fake_runner)
        names_both = "rust" in summary and "node" in summary
        markers_both = "RUST-MARKER" in summary and "NODE-MARKER" in summary
        ok = (ok_all is False) and names_both and markers_both
        print(f"[{'PASS' if ok else 'FAIL'}] lib: run_checks aggregates both stacks (ok=False, summary names both) -> ok={ok_all!r} summary={summary!r}")
        if not ok:
            fails.append("run_checks aggregates dual-stack results and names both")

    return fails


def scripts_repo_targeting_checks() -> list:
    """Regression for todo 427 defect 1: the scripts-repo row used to run
    the whole `ci/run_all.py` suite (all 46 `hooks/test_*.py` files,
    roughly 10 minutes - far past DEFAULT_TIMEOUT_SECONDS) on every turn
    that edited a hook `.py` file, which would time out and block every
    such turn. Reproduced with an injectable runner that RECORDS every
    argv it's called with, so the test can assert exactly which commands
    ran - py_compile + the one matched self-test, never `ci/run_all.py`.
    """
    fails = []
    lib = _testlib.load_module("testing_floor_lib_for_scripts_repo_test", _HOOKS_DIR / "_testing_floor_lib.py")

    with tempfile.TemporaryDirectory(prefix="testing-floor-scripts-repo-") as tmp:
        root = Path(tmp)
        (root / "ci").mkdir()
        (root / "ci" / "run_all.py").write_text("import sys; sys.exit(1)\n", encoding="utf-8")
        (root / "hooks").mkdir()
        (root / "hooks" / "foo-bar.py").write_text("x = 1\n", encoding="utf-8")
        (root / "hooks" / "test_foo_bar.py").write_text("print('ran')\n", encoding="utf-8")

        calls = []

        class FakeProc:
            def __init__(self):
                self.returncode = 0
                self.stdout = "ok"
                self.stderr = ""

        def fake_runner(argv, **kwargs):
            calls.append(argv)
            return FakeProc()

        ok_all, summary = lib.run_checks(root, runner=fake_runner, paths=["hooks/foo-bar.py"])
        expected = [
            [sys.executable, "-m", "py_compile", str(root / "hooks" / "foo-bar.py")],
            [sys.executable, str(root / "hooks" / "test_foo_bar.py")],
        ]
        ok = ok_all is True and calls == expected
        print(f"[{'PASS' if ok else 'FAIL'}] scripts-repo targeting: runs exactly py_compile + matched self-test, never ci/run_all.py -> calls={calls!r}")
        if not ok:
            fails.append("scripts-repo targeting: exact argv, no full suite")

        # No paths at all -> nothing targeted, passes, never calls the runner.
        def must_not_be_called(argv, **kwargs):
            raise AssertionError("runner must not be called when no paths are recorded")

        ok_empty, summary_empty = lib.run_checks(root, runner=must_not_be_called, paths=None)
        ok2 = ok_empty is True and "nothing targeted" in summary_empty
        print(f"[{'PASS' if ok2 else 'FAIL'}] scripts-repo targeting: no paths -> passes without running anything -> {summary_empty!r}")
        if not ok2:
            fails.append("scripts-repo targeting: no paths passes without running")

        # hooks/_hooklib.py has no test_hooklib.py pair -> py_compile only.
        calls2 = []

        def fake_runner2(argv, **kwargs):
            calls2.append(argv)
            return FakeProc()

        (root / "hooks" / "_hooklib.py").write_text("y = 2\n", encoding="utf-8")
        ok_all2, _summary2 = lib.run_checks(root, runner=fake_runner2, paths=["hooks/_hooklib.py"])
        ok3 = ok_all2 is True and calls2 == [[sys.executable, "-m", "py_compile", str(root / "hooks" / "_hooklib.py")]]
        print(f"[{'PASS' if ok3 else 'FAIL'}] scripts-repo targeting: a hook with no test pair runs py_compile only -> calls={calls2!r}")
        if not ok3:
            fails.append("scripts-repo targeting: no-pair hook is py_compile only")

    return fails


def node_test_script_checks() -> list:
    """Regression for todo 427 defect 2: the node row used to fire on bare
    `package.json` existence, so `npm test` would exit 1 ("Missing script:
    test") for a project that genuinely has no tests. Fixed to read
    `scripts.test` and treat npm's own default placeholder
    (`echo "Error: no test specified" && exit 1`) as no test script too.
    """
    fails = []
    lib = _testlib.load_module("testing_floor_lib_for_node_test_script", _HOOKS_DIR / "_testing_floor_lib.py")

    cases = [
        ({}, False, "no scripts key at all"),
        ({"scripts": {}}, False, "empty scripts object"),
        ({"scripts": {"test": ""}}, False, "empty test script string"),
        ({"scripts": {"test": 'echo "Error: no test specified" && exit 1'}}, False, "npm default placeholder"),
        ({"scripts": {"test": "vitest run"}}, True, "a real test script"),
    ]
    for pkg, expect_node, label in cases:
        with tempfile.TemporaryDirectory(prefix="testing-floor-node-script-") as tmp:
            root = Path(tmp)
            (root / "package.json").write_text(json.dumps(pkg), encoding="utf-8")
            stacks = lib.detect_stack(root)
            got_node = any(stack_label == "node" for stack_label, _argv in stacks)
            ok = got_node == expect_node
            print(f"[{'PASS' if ok else 'FAIL'}] node scripts.test: {label} -> node row present={got_node} (expected {expect_node})")
            if not ok:
                fails.append(f"node scripts.test: {label}")

    return fails


def run() -> int:
    fails = (
        unit_checks()
        + subprocess_checks()
        + real_detection_checks()
        + dual_stack_checks()
        + scripts_repo_targeting_checks()
        + node_test_script_checks()
    )
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
