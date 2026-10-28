<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=7, reconfirm-count=1, content-hash=8e91a176 -->
<!-- duplicate-checked -->
# figma_pixel_diff's --at flag silently drops all but the last point

**Type:** task
**Origin:** ai

## Goal

Make `--at` behave the same way in both sibling pixel tools, so passing it repeatedly samples every
point instead of silently sampling only the last one.

## Context

Found 2026-08-25 by todo `401`'s builder while verifying the shared-sampler extraction. It hit this
for real running the CLI, not by reading the source.

The two sibling tools parse the same flag differently:

- `skills/e2e/scripts/design_diff.py` - `--at` uses `action="append"`, so `--at 1,4 --at 4,1`
  samples BOTH points.
- `skills/figma-pixel-diff/scripts/figma_pixel_diff.py` - `--at` uses `nargs="+"`, so the same
  invocation **silently keeps only `4,1`**. The space-separated form `--at 1,4 4,1` is the one that
  works there.

Confirmed live during 401: `--at 1,4 --at 4,1` against `figma_pixel_diff.py` returned one result,
not two. There is no error and no warning - the dropped point simply never appears in the output,
which is the dangerous part. Anyone who learns the flag from `design_diff` and carries the habit
across gets a silently incomplete sample set.

This is pre-existing and unrelated to 401's refactor; 401 only made it visible by exercising both
CLIs side by side. The two tools now share `skills/_shared/pixel_utils.py`, which makes the
remaining surface inconsistency more surprising, not less.

## Approach

1. Pick ONE form and make both tools use it. `action="append"` is the better default: it fails
   loudly on a typo rather than silently absorbing an extra token, and it composes with other flags
   without ambiguity about where the list ends.
2. If `nargs="+"` must stay for backward compatibility with an existing caller, then accept BOTH
   (`action="append"` plus splitting any multi-value token) rather than leaving the two tools
   divergent.
3. Grep for existing callers of either flag before changing the parse - a skill body or script that
   already passes the space-separated form would break.

## Acceptance

- The same `--at` invocation samples the same points in both tools.
- Passing `--at a --at b` to `figma_pixel_diff.py` returns two results, not one.
- No existing caller of either script breaks; name the ones you checked.

## Notes

Also noted by 401's builder, and deliberately NOT filed as its own todo since it is one line of the
same fix: neither `sample_box` nor either caller validates coordinates against image bounds, so a
typo like `--at 9999,9999` produces a raw traceback rather than a clear message. Worth folding in
here if anyone touches this argparse code.
- Done via /mega-todos batch 4, commit d09a7ce: figma_pixel_diff --at is now action=append, matching design_diff.py, so repeated --at samples every point instead of keeping only the last. Confirmed non-breaking against the only existing caller.
