<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /autopilot and /delegate still carry the commit-cadence ambiguity todo 347 just fixed elsewhere

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/autopilot` and `/delegate` say, as `/auto-do-todos` and `/batch-todos` now do, that `/commit`
is invoked and read in full once per run and followed directly for every commit after.

## Context

Todo 347 fixed the contradiction in three places on 2026-08-16 (commit `7bb8751`): global
`CLAUDE.md`'s Git Commits bullet, `skills/auto-do-todos/SKILL.md` Step 6, and
`skills/batch-todos/SKILL.md` Step 6. All three now name the session marker, the prefilters, the
pathspec form and the branch/overlap checks as still applying to every later commit.

Two files were found carrying the same latent ambiguity and left alone because that dispatch did not
own them:

- `skills/autopilot/SKILL.md` lines 33, 89, 92: "the main loop runs `/commit` between chunks, since
  subagents stage but never commit".
- `skills/delegate/SKILL.md` line 54: "Runs `/commit` after subagent work lands".

Neither is sharply contradictory the way the original `/auto-do-todos` wording was, so this is
consistency work, not a live defect. It matters mainly because `/auto-do-todos` adopts
`/autopilot`'s behavior contract "in full", so the two should not disagree on how many times a skill
gets loaded.

Checked and needing nothing: `skills/mega-todos/SKILL.md` already phrases it correctly,
`snippets/auto-commit.md` and `skills/rate-it-and-commit/SKILL.md` describe single-commit cases only.

## Approach

Copy the wording todo 347 landed rather than inventing a third phrasing. The load-bearing clause is
the parenthetical naming what still applies per commit; without it the change reads as licence to
skip the prefilters, which is exactly wrong.

## Acceptance

- A cold run reading `/autopilot` or `/delegate` knows without inferring how many times to invoke
  `/commit`.
- The prefilter and pathspec requirements still visibly apply to every commit in both files.
- All five files agree.

## Notes

- Filed 2026-08-16 by `/auto-do-todos` from todo 347's builder report.
- Related: [[347-auto-do-todos-commit-cadence-is-unfollowable-as-written]] in `done/`.
- Done 2026-08-17: copied todo 347's exact wording into skills/autopilot/SKILL.md (Cadence bullet) and skills/delegate/SKILL.md (What the main agent still does itself). All five files now agree; the parenthetical naming prefilters, pathspec form and branch/overlap checks per commit is preserved verbatim.
