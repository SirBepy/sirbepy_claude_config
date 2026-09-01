<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=6, reconfirm-count=3, content-hash=3e29e095 -->
<!-- duplicate-checked -->
<!-- Grepped .claude/todos/ and done/ for pixel-diff / design screenshot / figma-pixel-diff: no todo hit. -->
# Skill: measure a rendered screenshot against a design screenshot

**Type:** skill-improvement
**Origin:** ai

## Goal

Package the "our UI vs the design mock" measurement loop as a skill, so it is not hand-rolled with
PIL every time a `make it match the design` task comes in.

## Context

2026-08-27, zng-app. Joe attached a screenshot of the built screen and a screenshot of the design
and said the component was "massive" versus design. Getting from that to real numbers took four
separate hand-written PIL passes in one session:

1. Crop both components and upscale to eyeball the border/divider treatment.
2. Threshold non-white pixels to get each component's bounding box.
3. Row/column profile to separate the true edges from the drop-shadow bleed, and to find internal
   features (the divider column, the text runs).
4. **Scale-normalize.** The two screenshots were at different zooms (707px wide vs 644px wide), so
   raw pixel sizes were not comparable. Normalized via a shared anchor - the glyph height of the
   same label in both - which gave a 1.31 factor and turned "55px tall in the mock" into "42 CSS px",
   matching a real `Spacing` token.

Step 4 is the part worth capturing: without it the comparison is worthless, and it is not obvious.
The payoff was concrete - design measured 114.5 x 42, the rebuilt component rendered 115.0 x 41.0.

The existing `/figma-pixel-diff` skill does not cover this: it fetches ONE node from the Figma API
and matches a sampled colour to a project token. This is two local rasters at unknown relative
scale, measuring geometry rather than colour, with no Figma access needed (and Figma quota is
scarce per `reference_figma_access_and_quota`).

## Approach

Either extend `/figma-pixel-diff` with a local-raster mode or add a sibling skill. It takes two
image paths plus an optional anchor description and returns:

- each image's scale factor, derived from a shared anchor the caller names (a label's glyph height
  works well; document that shadows and antialiasing inflate a naive bbox by 1-2px per side)
- the target element's bbox in both, normalized to CSS px
- the delta, and the nearest `Spacing` / design-token value for each dimension

Ship the PIL helper as a script in the skill folder rather than re-authoring the snippet inline.
Reuse the token-matching half of `figma-pixel-diff` instead of writing a second one.

## Acceptance

- Given two screenshots at different zooms and a named anchor, the skill reports both bboxes in
  comparable units plus the delta, with no hand-written PIL in the session transcript.
- The nearest-token lookup names a real constant from the target repo.
