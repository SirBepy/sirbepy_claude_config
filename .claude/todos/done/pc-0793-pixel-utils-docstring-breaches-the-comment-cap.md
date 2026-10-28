<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# pixel_utils.py's module docstring breaches the 4-line comment cap

**Type:** task
**Origin:** ai

## Goal

Trim `skills/_shared/pixel_utils.py:1-11` to the comment cap without losing the one thing in it that
the code genuinely cannot show.

## Context

Found by `/code-check` on 2026-08-25, reviewing commit `233b2a3` (todo 401's shared-sampler
extraction). Tagged BLOCKER by the reviewer because the quoted rule is a hard cap.

`~/.claude-fibo/CLAUDE.md`, Code Style: *"Comments: 2 lines typical, 4 lines HARD CAP per block...
never park a paragraph of design rationale in code - that belongs in the PR body, a PATTERNS/CLAUDE
doc, or the commit message."*

The file's module docstring is **11 lines** of extraction history plus an analysis of the
`getpixel()`-versus-numpy-slicing edge case. The file added 25 lines total, so the second clause
also bites: roughly 12 of 25 added lines are comment, about 48%, against a ~25% ceiling once a file
adds 20+.

**Why it slipped through:** `skills/commit/comment-noise.sh` does not inspect Python docstrings at
all, which is exactly todo `399`. So the prefilter passed it and the cap was never mechanically
tested. That makes this a real instance of 399's premise, worth citing there.

**Do not cut carelessly.** The reviewer's own caution: part of that docstring is the ONLY record
that `figma_pixel_diff`'s old radius-0 `getpixel()` path handled negative coordinates differently
(PIL list-style wraparound) and that no test covers it. That warning is load-bearing precisely
because nothing else asserts it. The extraction-history half is not - it is already in `233b2a3`'s
commit message and in `done/401-*.md`.

## Approach

1. Keep the edge-case warning, compressed to at most 2 lines: the numpy-slice semantics apply at
   every radius including 0, and negative or out-of-bounds coordinates are untested on both sides.
2. Delete the extraction narrative (dates, todo number, "extracted from near-identical copies").
   `git log` and `done/401-*.md` both already carry it.
3. Keep `sample_box`'s own short docstring - it documents the contract a caller needs (array is RGB,
   caller does the scaling), which is not history.
4. Re-run `bash skills/commit/prefilter-gate.sh skills/_shared/pixel_utils.py` and
   `python ci/run_all.py`.

## Acceptance

- No comment block in the file exceeds 4 lines.
- The negative/out-of-bounds warning still exists somewhere in the file.
- `python -m py_compile skills/_shared/pixel_utils.py` passes and both CLIs still run:
  `python skills/e2e/scripts/design_diff.py sample --img <png> --logical-width <w> --at 1,1`
  and `python skills/figma-pixel-diff/scripts/figma_pixel_diff.py sample --png <png> --at 1,1`
  must return the same hex for the same pixel.

## Notes

`python -m py_compile` passes regardless of comment length, so there is no mechanical test for this
finding - which is why `/code-check` classed it judgment and filed it rather than auto-applying it.
Cross-reference `399`; if 399 ships docstring coverage in `comment-noise.sh`, this file is a ready
made fixture for it.
- Done 2026-08-26: module docstring cut 11 lines to 4 (two 2-line blocks). Negative/out-of-bounds warning kept, extraction narrative dropped. Both CLIs return #1e1414 for --at 1,1 on an 8x8 scratch PNG; py_compile and prefilter-gate.sh clean.
