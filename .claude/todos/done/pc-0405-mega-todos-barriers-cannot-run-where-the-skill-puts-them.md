<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# /mega-todos puts its verify barriers inside the workflow script, where they cannot run

**Type:** skill-improvement
**Origin:** ai

## Goal

Correct `/mega-todos` Step D so its verify ladder sits where it can actually execute. As written the
skill describes barriers running inside the Workflow script, and a Workflow script has no way to run
a shell command.

## Context

Step D says to author a workflow with "a **barrier** every batch for the cheap ladder, and a second,
rarer barrier for the full one", and the verify-ladder table places the per-batch barrier, the full
floor and the final barrier inside the run.

A Workflow script's only primitives are `agent()`, `parallel()`, `pipeline()`, `log()`, `phase()`
and `workflow()`. It has no filesystem or shell access at all. So a barrier that runs
`python -m py_compile hooks/*.py` repo-wide cannot be a step in the script. The only ways to express
it are to spend a whole extra subagent per barrier purely to run three commands, or to run it in the
main thread after the workflow returns.

The 2026-08-19 run took the main-thread route and reported the deviation. It worked, and it also
composes better with Step E, which already mandates archival be main-thread-only because
`complete-todo.ps1` prunes the shared `PLAN.md`. But the skill's text still says otherwise, so the
next run either burns agents on barrier-only dispatches or deviates again.

This is the same shape as todos `358`, `369` and `347`: a skill stating an absolute that every real
run correctly ignores.

## Approach

1. Rewrite Step D's ladder so the per-batch and full-floor barriers are explicitly **main-thread**
   steps between `pipeline()` stages or after the workflow returns, not script steps.
2. Keep the per-todo cheap check where it is. That one genuinely belongs to the builder, which does
   have shell access.
3. Say why in one line, so nobody "fixes" it back: a Workflow script cannot run shell commands, and
   Step E already requires the main thread for archival anyway.
4. Re-check the `barrier` COMMIT_MODE section, which describes the barrier performing commits. That
   is already main-thread by necessity for the same reason and should read consistently.

## Acceptance

- Step D's ladder names which thread each rung runs on.
- Nothing in the skill implies a Workflow script can run a shell command.
- The `barrier` COMMIT_MODE description agrees with the rewritten ladder.

## Notes

- Fixed 2026-08-25. Step D's ladder table gained a 'Runs on' column: per-todo belongs to the builder, per-batch/full-floor/final all MAIN THREAD. Added the reason inline (a Workflow script's only primitives are agent/parallel/pipeline/log/phase/workflow, so it has no shell) plus an explicit do-not-burn-a-subagent-per-barrier line. Order-of-operations step 6 updated to match. Barrier COMMIT_MODE section re-read and already said main thread, so it needed no change. Confirmed live this session: this run's own barriers ran main-thread because they cannot run anywhere else.
