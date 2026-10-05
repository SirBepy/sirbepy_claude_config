---
name: figma-pixel-diff
description: Matches a Figma node's pixel color to the nearest project token, or diffs a local screenshot against a design mock.
argument-hint: "<figma-url-or-node-id>"
---

# /figma-pixel-diff

> Verify one Figma detail against an implementation: exact color, copy text, or layout, without
> hand-rolling PowerShell/Python one-liners each session.

## Two modes

- **Figma-fetch mode** (below): pull one node from the Figma API, sample its rendered PNG. Needs
  `FIGMA_TOKEN` and spends API quota.
- **Local-raster mode** (further down): compare two local screenshots you already have (a built
  screen vs. a design mock), no Figma access, no quota spent. Use this when both images already
  exist as files and the design mock did not come from a fetchable Figma node.

## Scope and quota

This tool is always scoped to a single node - it never sweeps a board. That is the deliberate
quota-safety design: use `figma-tiles` for a whole board section, this skill for "does this one
badge/chip/icon match Figma exactly". Fetches still go through
`skills/_shared/figma_client.py`'s cache and 429 backoff - always pass `--cache-dir` so re-running
the same node during a session costs zero extra quota.

## Setup

Set `FIGMA_TOKEN` as an environment variable (or add `FIGMA_TOKEN=<token>` to `~/.claude/.env`,
already gitignored). Generate a personal access token at figma.com > Settings > Personal access
tokens. Never hardcode a token in a script or commit one.

## Workflow

1. **Fetch the node** (tree JSON + rendered PNG, scale 2, cached):
   ```
   python skills/figma-pixel-diff/scripts/figma_pixel_diff.py fetch \
     --url <share-url-with-node-id> --out <dir> --cache-dir <persistent-cache-dir>
   ```
   Or pass `--file-key`/`--node-id` explicitly instead of `--url`.

2. **Sample exact colors** at pixel coordinates (read them off the fetched PNG visually first):
   ```
   python skills/figma-pixel-diff/scripts/figma_pixel_diff.py sample \
     --png <node.png> --at 120,48 --radius 2
   ```
   `--radius` averages a small square instead of one pixel, useful on anti-aliased edges.
   Repeat `--at` for multiple points (`--at 120,48 --at 4,1`); each becomes its own result.

3. **Crop a region** to inspect closely or hand to another tool:
   ```
   python skills/figma-pixel-diff/scripts/figma_pixel_diff.py crop --png <node.png> --box x0,y0,x1,y1 --out <crop.png>
   ```

4. **Cross-reference exact copy text and fill colors** from the JSON tree instead of eyeballing
   the render:
   ```
   python skills/figma-pixel-diff/scripts/figma_pixel_diff.py inspect --node-json <node.json> --name <substring>
   ```

5. **Map a sampled color to the nearest project token.** Build a `{tokenName: "#hex"}` JSON file
   from the project's own color source (e.g. a `CustomColors` class, a Tailwind config, a theme
   file) - this skill does not know any project's schema, so extracting that map is the caller's
   job:
   ```
   python skills/figma-pixel-diff/scripts/figma_pixel_diff.py nearest-token \
     --hex "#1a73e8" --tokens <tokens.json>
   ```
   Or sample directly from a PNG with `--png/--x/--y` instead of `--hex`. Reports `exact_match`,
   the nearest token and its distance, and `needs_new_token` (Euclidean RGB distance over
   `--threshold`, default 30) when nothing close exists - report that back rather than silently
   picking the nearest token.

## Note on color distance

The nearest-token match uses plain Euclidean RGB distance, not a perceptual color space (e.g.
CIEDE2000). It is a fast, dependency-free approximation, good enough to separate "exact" from
"clearly different" - treat a borderline `needs_new_token` result as a prompt to look at the crop,
not as ground truth.

## Local-raster mode: measuring a render against a design screenshot

Use this when you have two local PNGs - a built screen and a design mock - at possibly different
zoom levels, and need real px numbers instead of an eyeball guess. No Figma fetch, no quota. The
`crop` and `sample` commands above work on any PNG, Figma-fetched or not, so reuse them here; the
steps below cover the parts those commands don't do (bounding-box detection and scale-normalizing
between two zoom levels).

1. **Crop both images** to the component under review, for a side-by-side look:
   ```
   python skills/figma-pixel-diff/scripts/figma_pixel_diff.py crop --png <render.png> --box x0,y0,x1,y1 --out <render-crop.png>
   python skills/figma-pixel-diff/scripts/figma_pixel_diff.py crop --png <design.png> --box x0,y0,x1,y1 --out <design-crop.png>
   ```
   Upscale the crops in any viewer before measuring, to check border/divider treatment by eye.

2. **Measure both bboxes and scale-normalize in one call** with `measure`. Give it a *rough* region
   around the target in each image (a small margin, so the corners land on background - it does not
   need to be pixel-tight) and, when the two screenshots are at different zoom levels, a rough
   region around a shared anchor (a text label's glyph height is the reliable choice, since font
   rendering doesn't shift with a layout bug) in each image too:
   ```
   python skills/figma-pixel-diff/scripts/figma_pixel_diff.py measure \
     --render <render.png> --design <design.png> \
     --render-box x0,y0,x1,y1 --design-box x0,y0,x1,y1 \
     --anchor-render-box x0,y0,x1,y1 --anchor-design-box x0,y0,x1,y1 \
     --reference render
   ```
   Internally this: (a) thresholds each region against its own corner-sampled background and takes
   a row/column profile to find the true edges - a naive first-differing-pixel bbox over-reads by
   1-2px per side from drop-shadow bleed and antialiasing, so the cutoff is a fraction of the
   profile's max (`--row-frac`/`--col-frac`, default 0.5), not `> 0`; (b) computes
   `scale_factor = anchor_height_in_--reference / anchor_height_in_the_other_image` and applies it
   to the other image's target bbox. Omit both `--anchor-*-box` flags only when both screenshots are
   already known to be at the same zoom - the output then carries a `note` instead of a
   `scale_factor`, since raw pixels from two different zoom levels are not comparable. Which image
   is `--reference` is a per-task call - usually whichever is closer to 1:1 with CSS px (e.g. a
   browser screenshot at 100% zoom) - state which one and why.

3. **Match the normalized delta to a real token** with `nearest-token --value` (the numeric sibling
   of the color mode in step 5 of the Figma-fetch workflow above):
   ```
   python skills/figma-pixel-diff/scripts/figma_pixel_diff.py nearest-token \
     --value <normalized width or height from step 2> --tokens <spacing-tokens.json> --threshold <N>
   ```
   `--tokens` is `{tokenName: number, ...}` in this mode (vs `{tokenName: "#hex", ...}` for color) -
   build it from the project's own spacing/size scale (grep the theme/tokens file for the target
   repo), same as the color mode's tokens file. `--threshold` has no default in `--value` mode and
   must be passed explicitly: a Euclidean-RGB-calibrated default (30) would be meaningless against a
   spacing scale that steps by 4, or a font-size scale that steps by 2 - pick a threshold from the
   target scale's own step size.
