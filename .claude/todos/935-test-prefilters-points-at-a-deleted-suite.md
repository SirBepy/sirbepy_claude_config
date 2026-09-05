<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/922 removed the cap and deleted the suite; done/903 wrote the arithmetic test that was deleted. Neither covers the stale pointer or the coverage that went with it. -->
# test_prefilters.sh points at a suite that no longer exists

**Type:** task
**Origin:** ai

## Goal

`skills/commit/test_prefilters.sh` stops citing a deleted file, and the comment-noise cut arithmetic
either has a test or is explicitly recorded as uncovered.

## Context

Found 2026-09-05 by an independent `/code-check` review of the `a915c22..HEAD` range.

`skills/commit/test_prefilters.sh:5` still reads:

> Sibling test_comment_noise.sh (todo 903) already covers comment-noise.sh's cut-ratio math

Todo 922 deleted `skills/commit/test_comment_noise.sh` in the same range, so that sentence now points
at nothing.

The deletion itself was correct: those assertions tested that trimming to the cap cleared the GATE,
and comment-noise no longer gates anything. But the deleted suite also held the cut-arithmetic
checks (the exact-25%-boundary case from todo 903), and `comment-noise.sh` still computes and prints
`-> cut N comment lines` on every commit. That arithmetic now has zero test coverage.

So there are two separate things here, and they should not be conflated: a stale pointer, which is
just wrong, and a real coverage loss, which may or may not be worth restoring now that the number it
produces is advisory rather than enforced.

## Approach

1. Delete the stale sentence at `skills/commit/test_prefilters.sh:5`.
2. Decide whether the cut arithmetic is worth testing now that it only informs rather than blocks.
   Both answers are legitimate:
   - **Restore it**: add an arithmetic-only check into `test_prefilters.sh` (not a new sibling file).
     Cheap, and a wrong number printed at every commit is still misleading.
   - **Accept the loss**: say so in a comment where the old pointer was, naming what is no longer
     covered. An honest gap beats a silent one.
3. Do not restore the gate-based assertions. Those tested behaviour todo 922 deliberately removed.

## Acceptance

- No reference to `test_comment_noise.sh` survives anywhere in `skills/commit/`.
- Either an arithmetic check exists in `test_prefilters.sh`, or a comment states plainly that the cut
  arithmetic is untested and why that was accepted.
- `python ci/run_all.py` passes.
