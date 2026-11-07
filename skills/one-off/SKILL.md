---
name: one-off
description: "Triggers on /one-off <task> only: implements it immediately (no todo), then runs /code-check, /e2e, /commit (which runs /test), /close."
disable-model-invocation: true
argument-hint: "<task description>"
---

# /one-off

> Implement a described task immediately, then verify, commit, and close.

## 1. Implement

Treat the text after `/one-off` as the task to build right now, in this project. Skip the todos backlog, skip a design doc, skip asking for a plan - implement it end to end immediately. If a genuine decision point comes up that no existing pattern already dictates, ask it up front before the first edit; otherwise just build it.

## 2. Code-check

Run `/code-check` with `files:<the paths this task edited or wrote>`. It files its findings as todos by default and applies only the mechanical ones, but immediate execution is this skill's whole point, not a backlog: do each finding about code this task wrote now. Claim its todo with `~/.claude/skills/close/claim-todo.ps1 -Id <id>`, make the fix, then close it with `complete-todo.ps1 -Id <id>` (same folder). A finding about code this task did not touch stays filed.

## 3. E2E

Run `/e2e`, unless this invocation explicitly said not to (e.g. "no e2e").

## 4. Commit

Run `/commit`. It runs `/test` itself (its step 6b), so this skill has no separate test step: running it here too would repeat the same checks. If that run is red, or `/e2e` was, fix it and re-run the failing step before the commit lands.

## 5. Close

Run `/close --skip-review`. Step 2 already was the code-health review of this task's changes, and `/close`'s Phase 2 would run `/code-check` over the same commits a second time.
