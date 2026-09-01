<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=4, reconfirm-count=1, content-hash=854ef532 -->
<!-- duplicate-checked -->
<!-- Grepped .claude/todos/ and done/ for _testlib / run_main / guard test harness: done/501 and done/250 are the parents, no live match. -->
# The monkeypatched run_main harness is repeated in four new guard suites

**Type:** skill-improvement
**Origin:** ai

## Goal

Fold the last piece of guard-test boilerplate into `hooks/_testlib.py`, so a new guard suite does
not start by redefining the same five-to-eight-line `run_main` shim.

## Context

Filed 2026-08-31 by an independent `/code-check` reviewer over a `/mega-todos` run's whole diff.

Todo `501` added five new guard self-test suites in one dispatch. Four of them independently define
the same local helper: monkeypatch the guard's `read_payload` with a lambda returning a payload
dict, call `guard.main()`, catch `SystemExit`, return its code.

- `hooks/test_commit_guard.py:37-45`
- `hooks/test_pr_guard.py:60-67`
- `hooks/test_flutter_workdir_guard.py:33-38`
- `hooks/test_package_manager_guard.py:103-108`

`hooks/_testlib.py` already centralises `load_module`, `report`, `run_cases` and `summarize` for
exactly this family of files, so this is the one remaining shared shape that never got folded in.
It was written four times in parallel by four agents in the same batch, which is why it converged on
an identical shape without anyone noticing the duplication.

This is genuinely minor. It is filed because it is cheap and because `_testlib.py` is the obvious
home, not because anything is broken.

## Approach

1. Read all four call sites first. Each guard's `read_payload` takes a slightly different payload
   shape, so the helper must let the CALLER build the payload rather than assuming a schema.
2. Add `run_guard_main(guard, payload) -> int` to `hooks/_testlib.py`: monkeypatch
   `guard.read_payload`, call `guard.main()`, catch `SystemExit`, return the code.
3. Replace the four local definitions with calls to it. Do not change any test's assertions while
   doing so; this is a pure extraction and the suite must stay green throughout.
4. Leave any suite whose shim genuinely differs alone, and say which and why.

## Acceptance

- [ ] `hooks/_testlib.py` exposes the shared helper
- [ ] The four suites call it instead of defining their own
- [ ] No test assertion changed, and `python ci/run_all.py` exits 0 with the same suite count
- [ ] Any suite deliberately left with its own shim is named with a reason

## Notes

- Worth roughly a 4. Pure hygiene on brand-new code with no defect behind it. Worth doing only while
  someone is already in `hooks/_testlib.py` for another reason.
- Care warranted: `hooks/_testlib.py` is imported by every guard suite, so a mistake here fails the
  whole CI run rather than one file. That is the opposite risk profile from the change's size.
