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
    the string "raise" (fault injection for the fail-open path)."""
    def _fn(root):
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
    TESTING_FLOOR_FAKE_CHECK stub) against a tiny fake `ci/run_all.py` that
    genuinely exits 1 or 0 - the todo's own instruction that the gate must
    be proven against a deliberately-broken case, not just a stubbed one.
    """
    fails = []
    with tempfile.TemporaryDirectory(prefix="testing-floor-guard-real-") as tmp:
        tmp_path = Path(tmp)

        # A deliberately-broken "project": its ci/run_all.py always fails.
        broken_root = tmp_path / "broken-project"
        (broken_root / "ci").mkdir(parents=True)
        (broken_root / "ci" / "run_all.py").write_text(
            textwrap.dedent("""
                import sys
                print("FAIL: this project's fast checks are deliberately broken")
                sys.exit(1)
            """).strip() + "\n",
            encoding="utf-8",
        )
        state_dir_broken = tmp_path / "state-broken"
        session_broken = "sess-broken"
        flag_broken = state_dir_broken / session_broken
        state_dir_broken.mkdir(parents=True)
        flag_broken.write_text(json.dumps({"attempts": 0, "root": str(broken_root)}), encoding="utf-8")
        proc = run_hook({"session_id": session_broken}, {"TESTING_FLOOR_STATE_DIR": str(state_dir_broken)})
        ok = proc.returncode == 0 and '"decision": "block"' in proc.stdout and "deliberately broken" in proc.stdout
        print(f"[{'PASS' if ok else 'FAIL'}] real-detection: a genuinely failing ci/run_all.py blocks the turn -> exit={proc.returncode} stdout={proc.stdout.strip()!r}")
        if not ok:
            fails.append("real detection: failing case blocks")

        # A genuinely passing "project": its ci/run_all.py always succeeds.
        passing_root = tmp_path / "passing-project"
        (passing_root / "ci").mkdir(parents=True)
        (passing_root / "ci" / "run_all.py").write_text(
            textwrap.dedent("""
                print("OK: all checks passed")
            """).strip() + "\n",
            encoding="utf-8",
        )
        state_dir_pass = tmp_path / "state-real-pass"
        session_pass = "sess-real-pass"
        flag_pass = state_dir_pass / session_pass
        state_dir_pass.mkdir(parents=True)
        flag_pass.write_text(json.dumps({"attempts": 0, "root": str(passing_root)}), encoding="utf-8")
        proc2 = run_hook({"session_id": session_pass}, {"TESTING_FLOOR_STATE_DIR": str(state_dir_pass)})
        ok2 = proc2.returncode == 0 and proc2.stdout.strip() == "" and not flag_pass.exists()
        print(f"[{'PASS' if ok2 else 'FAIL'}] real-detection: a genuinely passing ci/run_all.py allows the turn and clears the flag -> exit={proc2.returncode} stdout={proc2.stdout.strip()!r}")
        if not ok2:
            fails.append("real detection: passing case allows")

    return fails


def run() -> int:
    fails = unit_checks() + subprocess_checks() + real_detection_checks()
    return _testlib.summarize(fails)


if __name__ == "__main__":
    sys.exit(run())
