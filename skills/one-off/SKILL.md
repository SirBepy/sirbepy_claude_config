---
name: one-off
description: "Triggers on /one-off <task> only: implements it immediately (no todo), then runs /code-check, /test, /e2e, /commit, /close."
disable-model-invocation: true
argument-hint: "<task description>"
---

# /one-off

> Implement a described task immediately, then verify, commit, and close.

## 1. Implement

Treat the text after `/one-off` as the task to build right now, in this project. Skip the todos backlog, skip a design doc, skip asking for a plan - implement it end to end immediately. If a genuine decision point comes up that no existing pattern already dictates, ask it up front before the first edit; otherwise just build it.

## 2. Code-check

Run `/code-check`. If it surfaces anything worth doing, do it now instead of filing it - immediate execution is this skill's whole point, not a backlog.

## 3. Test

Run `/test`.

## 4. E2E

Run `/e2e`, unless this invocation explicitly said not to (e.g. "no e2e").

## 5. Fix any red

If `/test` or `/e2e` turned up anything red, fix it and re-run the failing step before moving on.

## 6. Commit

Run `/commit`.

## 7. Close

Run `/close`.
