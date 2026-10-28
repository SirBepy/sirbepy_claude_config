<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=7, reconfirm-count=1, content-hash=9adb4b78 -->
# The four hook test files each reimplement the same loader and runner

**Type:** task
**Origin:** ai

## Goal

Extract the module loader and the case runner that all four `hooks/test_*.py` files duplicate into
one shared place, so a fifth hook test does not copy it a fifth time.

## Context

Found by the `/code-check` pass of the 2026-08-13 `/auto-do-todos` session, which wrote all four
files within hours of each other through four separate builder dispatches. None of them saw the
others, so each independently invented the same two things.

The duplicated pieces:

- A loader that pulls the target hook in by path via `importlib.util.spec_from_file_location` plus
  `exec_module`, because hook filenames contain hyphens and are therefore not importable by name.
- A runner that walks a list of cases, prints `[PASS]` or `[FAIL]` per case, prints `ALL PASS` or a
  failure list at the end, and exits 0 or 1.

Sites, with the loader block first and the runner block second in each:

- `hooks/test_bare_question_detector.py:9-21` and `:99-106`
- `hooks/test_command_chaining_detector.py:9-18` and `:37-50`
- `hooks/test_em_dash_guard.py:7-18` and `:73-80`
- `hooks/test_shell_content_write_guard.py:7-15` and `:41-55`

`hooks/_hooklib.py` already exists as the designated shared scaffold for hooks, and none of the four
uses it.

## Approach

Add `load_module(name, path)` and `run_cases(cases, fn) -> int` and have all four import them.

Decide where they live before writing. `_hooklib.py` is imported by the PRODUCTION hooks at runtime,
so putting test-only helpers in it means every hook invocation parses code it never calls. A sibling
`hooks/_testlib.py` avoids that for the cost of one more file. Lean towards `_testlib.py` unless the
added helpers are genuinely tiny.

Keep the output format byte-identical. These suites are read by humans scanning for `ALL PASS`, and
a refactor that quietly changes the report is worse than the duplication.

## Acceptance

- All four suites import the shared helpers rather than defining their own.
- Each still passes, and its printed output is unchanged from before the refactor.
- A grep for `spec_from_file_location` under `hooks/` returns only the shared helper.

## Notes

- Filed by `/close` Phase 2 on 2026-08-13. Not urgent: the duplication costs nothing at runtime, it
  only guarantees the next hook test copies it again.
- Completed via /auto-do-todos 2026-08-15: added hooks/_testlib.py (load_module, run_cases, report, summarize) and migrated all FIVE test_*.py suites, not the four the todo named - test_shortcut_create_guard.py had already copied the harness a fifth time, exactly as the todo predicted. No sys.path fiddling needed: CPython prepends the script own directory to sys.path[0] under python hooks/test_x.py, so a bare import _testlib resolves. Before/after output verified byte-identical for all five.
