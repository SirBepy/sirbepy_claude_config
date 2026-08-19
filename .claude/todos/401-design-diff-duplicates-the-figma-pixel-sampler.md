<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# design_diff.py re-implements figma-pixel-diff's pixel sampler almost line for line

**Type:** task
**Origin:** ai

## Goal

Extract the shared pixel-sampling and hex-formatting helpers into one place so the two scripts stop
carrying near-identical copies.

## Context

`skills/e2e/scripts/design_diff.py` landed 2026-08-19 (commit `e5b0646`, todo 362) and was written
without sight of `skills/figma-pixel-diff/scripts/figma_pixel_diff.py`, because the run that built it
was 33 parallel agents that never saw each other's files.

The duplication, found by a `/code-check` DRY pass:

- `design_diff.py:36-37,98-100,190-198` - `hexc()`, `sample_pixel()`, `cmd_sample`
- `figma_pixel_diff.py:32-33,40-49,68-74` - `rgb_to_hex()`, `sample_pixel()`, `cmd_sample`

Same format string, same average-an-RGB-box-then-format pattern, same `--at`/`--radius` subcommand
shape. They differ only in input (a numpy array already in memory versus a PNG path opened via PIL)
and in that one applies a logical-px/DPR scale factor first.

`skills/_shared/` already exists and already holds `figma_client.py`, so there is a home for this.

## Approach

1. Extract `hex_from_rgb()` and `sample_box()` into `skills/_shared/pixel_utils.py`.
2. Have both scripts import them. `design_diff.py` wraps the shared sampler with its own DPR scale
   step rather than forking it.
3. Keep each script's own `cmd_sample` CLI surface: the argparse wiring is not the duplication, the
   maths is.
4. Verify both scripts still produce identical output on the same input before and after. A colour
   sampler that silently shifts by a pixel is the kind of regression no test here would catch.

## Acceptance

- One implementation of the box-average and the hex format, imported by both.
- Both scripts produce byte-identical output to before on a sample image.
- `skills/_shared/pixel_utils.py` compiles and both scripts pass `python -m py_compile`.

## Notes

- `design_diff.py` is 244 lines, `figma_pixel_diff.py` smaller; neither is near the 400-line split
  threshold, so this is purely about the duplicated maths.
