<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=7, reconfirm-count=1, content-hash=37c78700 -->
<!-- duplicate-checked: 469 is the handoff-mode conflict with the same hook, a different caller -->
# cleanup-todos Step 7 merge write is blocked by todo-duplicate-guard, and is wasted right before /loop-todos

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/cleanup-todos` Step 7's file-overlap merge (Step 4.5 proposals) actually completable
unattended, and skip it when the caller is about to execute the sources anyway.

## Context

Hit 2026-10-08 in shop-scraper, an unattended Jarvis run (`/cleanup-todos` then `/loop-todos 5`).
Step 4.5 found an all-ai group (todos 34 + 35, both targeting
`.claude/skills/evaluate-phones/SKILL.md`), so Pass A tried to write the merged todo 36. The Write
was rejected by `hooks/todo-duplicate-guard.py`: "Possible duplicate of existing todo(s): 34-...,
35-...". That is by construction: a merged todo always shares vocabulary with its own sources, which
are still live until `complete-todo.ps1` archives them in step 3, AFTER the write. Step 7's Merge
section never mentions the guard or the `<!-- duplicate-checked -->` escape.

Separately, the merge bought nothing: `/loop-todos` executed both sources together minutes later,
so the merged file would have been written and archived in the same run. The run abandoned the
merge, deleted the `36-.reserved` marker, and executed 34 + 35 directly.

## Approach

- `skills/cleanup-todos/SKILL.md` Step 7 "Merge", step 2: tell the writer to include
  `<!-- duplicate-checked: merge of <ids> -->` in the merged file, since the guard always fires on
  a merge's own sources.
- Same file, Step 4.5 or Step 7: when invoked as the first step of an execution run
  (`/auto-do-todos` Step 2, `/loop-todos`), skip writing merges for all-ai groups whose members are
  all EASY/AUTO and report them as "will be executed together" instead.

## Acceptance

- A Pass A merge in an unattended run writes its merged todo without a hook rejection.
- A `/loop-todos` run does not write and archive a merged todo inside the same run.

## Notes

- Filed from shop-scraper's /close on 2026-10-08.

## Answers 2026-10-08

- Joe, 2026-10-08 (todo-questions chat): approved to build as written.
