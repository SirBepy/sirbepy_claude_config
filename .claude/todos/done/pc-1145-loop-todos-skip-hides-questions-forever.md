<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=HARD, worth=8, reconfirm-count=1, content-hash=5dcae258 -->
# /loop-todos Phase 0 "skip" makes a todo's questions invisible to every later run

**Type:** skill-improvement
**Origin:** ai

## Goal

A todo skipped in `/loop-todos` Phase 0 (dev chose "skip this todo", or an unattended run routed a hard stop to skip) must still have its questions asked on a later run, instead of dropping out of every future question round.

## Context

`skills/loop-todos/SKILL.md` Phase 0 step 4's table says a Skipped todo gets its heading renamed `## Open questions` -> `## Deferred questions` plus a `<!-- loop-skip: ... -->` comment. But Phase 0 step 1 only collects `## Open questions` blocks, and `/auto-do-todos` Step 4/5 only scan `## Open questions` too. Nothing anywhere reads `## Deferred questions` or the `loop-skip` marker back, apart from Phase 0 step 5, which uses it to EXCLUDE the todo.

So a skip is permanent: the questions never reach the dev again unless someone opens the file by hand.

Observed 2026-10-08 in ssy-mobile, during an unattended overnight `/loop-todos 5` dispatched by Jarvis. The invoking prompt said to treat hard stops as "skip this todo". Two dev-origin todos (`0003-pc-mac-agent-bridge.md`: needs the Mac awake plus a user-scope MCP config; `0004-clockify-shelved-wednesday-blocks.md`: needs a billing fact only Joe holds and an outbound Clockify write) were renamed to `## Deferred questions` as the table says. Both questions are things Joe genuinely has to answer later, and as written no future run will ask him.

The unattended case makes it worse: there the "skip" is an automatic routing of a hard stop, not the dev's own decision to defer, yet it gets the same permanent treatment.

## Approach

Pick one in `skills/loop-todos/SKILL.md`:

- Scope the skip to the current loop only: keep the `## Open questions` heading, and track the skip list in the loop's state block (Phase 4 already carries `Skipped todos: <ids>`) instead of mutating the file. Probably the simplest fix.
- Or keep the rename, but make Phase 0 step 1 also collect `## Deferred questions` blocks, with a note that the dev deferred them on `<date>`.

Also decide whether an unattended run's auto-skip should mutate the file at all.

## Acceptance

- After a run skips a todo, the next attended `/loop-todos` or `/auto-do-todos` run still surfaces that todo's questions.
- Phase 0's table and step 1 agree on which headings are read back.

## Notes

- Filed from ssy-mobile `/close` on 2026-10-08. The two ssy-mobile todos above currently carry `## Deferred questions`; revert them to `## Open questions` once this is fixed, or by hand if Joe wants them asked sooner.
- Done 2026-10-08 per Joe's answer: loop-todos Phase 0 step 1 also collects ## Deferred questions, a new step 2 asks one coarse 'we have N deferred questions, answer them now?' first, answered deferred blocks drop their heading and loop-skip marker, and the skip list is re-read after write-back. /auto-do-todos Step 4 states deferred blocks are loop-todos Phase 0's state only. The two ssy-mobile todos (0003, 0004) will now be offered on that repo's next /loop-todos run.

## Answers 2026-10-08

- Joe, 2026-10-08 (todo-questions chat): keep the `## Deferred questions` rename, and make later runs read those blocks back. Phase 0 offers them first as one coarse question: "we have N deferred questions, answer them now?", and only on yes asks them one by one.
