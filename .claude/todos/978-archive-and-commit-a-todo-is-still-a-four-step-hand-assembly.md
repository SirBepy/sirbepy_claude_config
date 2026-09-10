<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/964 scripted the COMMIT half and is closed; done/932 fixed
     archive-batch.ps1's pathspec bug. Neither joins the two, and neither touches the --own
     recomputation this describes -->
# Archiving a todo and committing it is still a four-step hand assembly, done 25+ times a run

**Type:** skill-improvement
**Origin:** ai

## Goal

Collapse the archive-then-commit ceremony into one call, so a backlog run stops hand-assembling the
same four steps per todo.

## Context

Filed 2026-09-10 from `/close` Phase 1 of a `/loop-todos` run that closed 60 todos in one session.
The ceremony below ran more than 25 times, by hand, every time:

1. `complete-todo.ps1 -Id <id> -Note "<...>"` (appends the Notes line, moves to `done/`, releases
   the claim, prunes PLAN.md).
2. `git add` the new `done/` path, because a pathspec cannot name a file git does not know yet.
3. Assemble the pathspec: the source files the work touched, PLUS the `done/<id>-*.md` destination,
   PLUS the now-deleted `.claude/todos/<id>-*.md` source. Forgetting the third is the exact bug
   `done/932` fixed in the `/mega-todos` helper, and it stays hand-assembled everywhere else.
4. `commit-pathspec.sh --expect-branch ... --expect-sha ... --own ... -m "..." -- <all of the above>`.

Step 4 also carries its own repetition: `--own` was rebuilt from
`git log --format=%H <session-start>..HEAD` before every single call, because the script has no way
to express "commits this session made". That is a shell substitution retyped 25 times.

`done/964` scripted the eight-step commit chain itself and is the reason step 4 is one call rather
than eight. This todo is the layer above it: nothing joins archival to that call.

Not urgent. Nothing here is wrong, and each step has a guard behind it. It is repetition, and the
kind that invites a skipped step on the 26th repeat.

## Approach

1. Add `--own-since <sha>` to `skills/commit/commit-pathspec.sh`, resolving to
   `git log --format=%H <sha>..HEAD` internally. That alone removes the retyped substitution and is
   independently useful. Keep `--own` as-is for the explicit case.
2. Then decide, deliberately, where archival belongs. Two candidates, and they are not equivalent:
   - a `--archive <id>[,<id>...]` flag on `commit-pathspec.sh`, which would make a commit script
     also move files, muddying a script whose current virtue is that it only verifies and commits;
   - a thin wrapper beside `complete-todo.ps1` that archives, resolves the three-part pathspec, and
     shells out to `commit-pathspec.sh`.
   The wrapper is probably right for exactly the reason the first option is tempting, but confirm it
   against how `skills/mega-todos/archive-batch.ps1` already solves the batch case rather than
   inventing a third shape.
3. Whatever lands must derive the deleted-source path itself. That is the step most often forgotten
   by hand and the one `done/932` proves is easy to get wrong.

## Acceptance

- One call archives a todo and commits it with a correct three-part pathspec.
- `--own-since` works and the old `--own` form is unchanged, proven by a case for each.
- A test beside `skills/commit/test_commit_pathspec.sh` covers the archive shape, including that the
  deleted source is in the commit.
- `python ci/run_all.py` exits 0.

## Notes

- Read `done/964` first for what `commit-pathspec.sh` already guarantees, and `done/932` for the
  deletion-half bug this must not reintroduce.
- Resist widening this into "a skill for closing todos". The gap is four mechanical steps, not a
  missing workflow.
