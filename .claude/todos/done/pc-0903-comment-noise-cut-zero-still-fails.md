<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: about comment-noise.sh's own boundary reporting, not the cap value or what it counts -->
# comment-noise.sh says "cut 0 comment lines" while still exiting non-zero at exactly 25%

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `skills/commit/comment-noise.sh` print a cut count that, when acted on, actually clears the
gate. Right now a file sitting exactly on the threshold reports `cut 0` and still fails.

## Context

Observed 2026-09-03 while committing in `claude_usage_in_taskbar`. Two consecutive gate runs on
`src/shared/chat/composer.ts`:

    src/shared/chat/composer.ts 13/49 (26%) longest 4 -> cut 1 comment lines     EXIT=1
    src/shared/chat/composer.ts 12/48 (25%) longest 4 -> cut 0 comment lines     EXIT=1

The first message was actionable. After cutting the one line it asked for, the second run printed
`cut 0 comment lines` - which reads as "nothing left to do" - and still exited 1, because the
ratio check treats 25% as a failure (inclusive) while the cut arithmetic computes lines needed to
get *to* 25% rather than *below* it. The only way forward was to guess and cut another line.

Cost is a full extra gate round-trip per hit, and worse, `cut 0` invites the reader to conclude
the gate is broken and reach for a bypass.

## Approach

In `skills/commit/comment-noise.sh`, wherever the required-cut count is derived:

1. Decide and document which way the boundary goes. The cap in `comment-noise.md` reads "under
   ~25%", so exit-1 at exactly 25% is the correct behaviour - the arithmetic is what is wrong.
2. Compute the cut as the lines needed to land strictly below the threshold, so a flagged file
   never reports `cut 0`.
3. Add a self-test covering the exact-boundary case (a file at precisely 25%) to whichever
   `hooks/test_*.py` or shell test suite `python ci/run_all.py` already runs.

## Acceptance

- A file at exactly 25% comment lines reports `cut 1` (or more), never `cut 0`.
- Acting on the printed number once makes the next run exit 0, in a single retry.
- `python ci/run_all.py` passes.

## Notes

- Completed in /mega-todos wave 1, commit 3ea2f0b: cut is now int((4*c-add)/3)+1, the smallest cut landing strictly below 25 percent, so an exactly-25-percent file reports cut 1 rather than an unsatisfiable cut 0. Added skills/commit/test_comment_noise.sh covering the boundary.
