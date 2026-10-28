<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=6, reconfirm-count=1, content-hash=53297c87 -->
<!-- duplicate-checked: 484 (done) moved claiming to where work starts for dispatched work; 1042 is the orchestrator-dispatch case; this is the inline-executor case -->
# /loop-todos on a tiny backlog edits a todo's target files before claiming it

**Type:** skill-improvement
**Origin:** ai

## Goal

An inline `/loop-todos` -> `/auto-do-todos` run cannot edit a todo's target files while that todo is unclaimed.

## Context

2026-10-08, sirbepy_tauri_kit overnight run (session da99a0aa). Backlog held one todo (0001). `/cleanup-todos` ran its small-backlog inline branch, which reads every todo and re-verifies it against the tree, and the orchestrator went from that verification straight into editing `.github/workflows/tauri-windows-release.yml` and `workflow-templates/tauri-release.yml`. The claim (`claim-todo.ps1 -Id 0001`) only happened after commit b04c723 had already landed. The claim call lives in `/auto-do-todos` Step 6 (`skills/auto-do-todos/SKILL.md`, "Claim the whole AUTO queue in one call before grinding it"), a remembered step. With a 1-todo backlog Steps 3-5 collapse to nothing, so nothing separates the cleanup read from execution and the Step 6 claim is easy to skip. No hook flagged the unclaimed edits. No harm this time (no peers), but the same skip would race a peer on a shared backlog.

## Approach

Options, cheapest first:
- `/loop-todos` Phase 1 step 2: claim the AUTO queue as part of the cycle driver itself (one `claim-todo.ps1 -Id <ids>` call printed as the cycle's first action), so the inline path cannot reach an edit without passing it.
- Or a PreToolUse Edit/Write advisory in a repo whose `.claude/todos/` has open todos and no `.claims/` file from this session: a one-line reminder, not a block.

Rejected: restating "claim first" in more prose; that is the failure 484 already moved away from.

## Acceptance

- A `/loop-todos` run over a 1-todo backlog shows the claim call before the first Edit to that todo's target files.

## Notes

- Done 2026-10-08 per Joe's answer: loop-todos Phase 1 step 2 claims every backlog id in one claim-todo.ps1 call as the cycle's first action, and /auto-do-todos Step 6 skips its own claim inside a loop (claim-todo.ps1 would misread its own session's claim as held by a live peer, it compares pid liveness, not session ids).

## Answers 2026-10-08

- Joe, 2026-10-08 (todo-questions chat): claim in the cycle driver. `/loop-todos` Phase 1 prints the `claim-todo.ps1 -Id <ids>` call as the cycle's first action. No advisory hook.
