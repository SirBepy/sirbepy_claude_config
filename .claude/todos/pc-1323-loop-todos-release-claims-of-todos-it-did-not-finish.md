<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no existing todo mentions loop-todos claim cleanup; pc-1147-era notes only added the up-front claim -->
# /loop-todos claims every backlog id up front and nothing releases the ones it does not finish

**Type:** skill-improvement
**Origin:** ai
**Summary:** `/loop-todos` Phase 1 step 2 claims all backlog ids in one batch, but only `complete-todo.ps1` removes a claim, so every todo the loop leaves open keeps a claim file that blocks other sessions until it goes stale.

## Why

A `/loop-todos` run on the rodge backlog (2026-11-05) claimed 42 todos; 15 were archived (their claims removed by `complete-todo.ps1`), 27 stayed open and kept `.claude/todos/.claims/<id>.claim`. The run's own cleanup `Remove-Item` over those files was denied by the auto-mode classifier (Irreversible Local Destruction), and `claim-todo.ps1` has no release option, so the claims were left behind.

## Goal

At the end of a `/loop-todos` run (and of each cycle that hands off to a successor), the claims this session holds on todos it did not complete are released through a sanctioned script, so a peer chat can claim them at once.

## Approach

1. Add `-Release` (one or more ids, optional `-AllMine`) to `skills/close/claim-todo.ps1` that deletes only claim files whose recorded session id matches the current session.
2. Call it from `skills/loop-todos/SKILL.md` Phase 5 (before the final report) and from Phase 4's respawn path, naming the ids still claimed.
3. A respawned successor re-claims in its own Phase 1 step 2, so the handoff must release first or the successor reads its predecessor's claims as a live session's.

## Acceptance

- After a loop run, `.claude/todos/.claims/` holds claims only for todos a live session is working on.
- A test of `-Release` leaves another session's claim untouched.
