<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Resolve rate-it-and-commit's pending decision on skills/mockup/SKILL.md

**Type:** task

## Goal

`skills/mockup/SKILL.md` was rated 4/10 by a rating subagent via `/rate-it-and-commit`
(threshold 8, not met). The dev is fixing the skill up in a separate chat and has not yet
answered the below-threshold "what now" question (iterate first and commit / commit anyway /
abandon). Nothing has been committed. Once the dev's other chat produces an updated version of
the skill, resolve this properly (re-rate if changed materially, then commit or abandon per
the dev's call) instead of leaving the file sitting uncommitted indefinitely.

## Context

Original rating subagent findings (2026-07-17): the real-component branch (step 3, scratch
routes built from real app components) has no disposal/cleanup step and no requirement to pass
the project's Testing & verification floor if the dev decides to keep the scratch route - unlike
the standalone-file branch (step 4) which is clean by construction (`.for_bepy/mockups/`,
gitignored, never touches real code). Suggested lifts topped out around 7/10 individually; none
alone reached the 8/10 threshold.

Full rating text was handed to the dev to paste into the other chat - see this session's
transcript around 2026-07-17 for the complete rating block if needed.

Design decisions already locked in for this skill (from an earlier `/brainstorm`-style
AskUserQuestion round in this same session, do not re-litigate unless the other chat's fix
changes them): manual `/mockup` trigger only, always fires `/brainstorm` first if the specific
idea is unexplored, branches on web-stack-with-components vs Flutter/greenfield, no separate
`mockup-style.md` file, defers to existing `/supervised-run` + screenshot flow for showing
results to the dev.

## Approach

1. Check whether `skills/mockup/SKILL.md` has been edited since 2026-07-17 (the other chat's
   fix-up). If so, treat the below-threshold rating as stale.
2. If materially changed: re-rate via `/rate-it` (or `/rate-it-and-commit`) before committing.
3. If unchanged: ask the dev directly whether to commit as-is, iterate here, or abandon - the
   original question timed out unanswered.

## Acceptance

- `skills/mockup/SKILL.md` is either committed with a rating that met threshold (or an explicit
  "commit anyway" from the dev), or the file/task is explicitly abandoned - not left in limbo.

## Notes

This file itself will go stale fast (the other chat is actively editing the skill). If picked up
long after 2026-07-17, verify current file state before trusting anything above as still true.
- Dropped via /cleanup-todos 2026-08-11: already done - skills/mockup/SKILL.md commit 091d6cdf fixed the exact flagged gap. Confirmed by dev 2026-08-11.
