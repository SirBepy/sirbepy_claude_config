<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1272 is about pointing a CLAUDE.md rule at red-check.ps1, a different surface -->
# test-archive-batch.ps1 scenario 2 fails: its "pre-fix" replay reads HEAD, which already has the fix

**Type:** task
**Origin:** ai
**Summary:** The mega-todos archive-batch test fails on every run because its "before the fix" scenario actually replays the fixed script.

## Goal

`powershell -File skills/mega-todos/test-archive-batch.ps1` exits 0 again, with scenario 2 still proving the pre-fix bug or removed on purpose.

## Context

Found by the 2026-10-30 pre-push `/code-check` (reviewer ran the test: "FAIL: pre-fix .Pathspec OMITS the tracked source", "FAIL: pre-fix code leaves a stray staged deletion behind", "FAIL: 2 assertion(s) failed", exit 1). Not re-run by the filing session.

- `skills/mega-todos/test-archive-batch.ps1:121-123,129,149`: scenario 2 replays `git show HEAD:skills/mega-todos/archive-batch.ps1` as the pre-fix script, but HEAD has carried that fix since 4c0e2f3, so the replay is the fixed code.
- b232631 (device-prefixed todo ids) edited this scenario (helpers from HEAD, legacy seeding) without making it pass.
- `ci/run_all.py:176` says this test is not discovered, so CI never sees it.

## Approach

Pin scenario 2 to the pre-fix commit (`4c0e2f3~1`) and take its `_shared.ps1` and `complete-todo.ps1` from that same commit. If the old helpers cannot run against the label-aware tree, delete scenario 2 and keep scenarios 1, 3 and 4.

## Acceptance

- The test exits 0.
- Scenarios 1, 3 and 4 still assert what they assert today.
