---
name: figma-pixel-diff
description: Fetches one Figma node, samples/crops its rendered PNG, and matches a pixel color to the nearest project token. Also measures a local render screenshot against a design screenshot at a different zoom, via a shared anchor.
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

2. **Find each true bounding box by thresholding**, not by eyeballing the crop box: scan for the
   first/last row and column where a pixel differs from the background beyond a small tolerance.
   Neither `crop` nor `sample` does this - there is no bbox-detection command in this skill today
   (see "Not built yet" below), so this step is a short ad-hoc script per session until one exists.
   A naive threshold over-reads by 1-2px per side from drop-shadow bleed and antialiasing; step 3
   corrects for that.

3. **Take a row/column profile** of the thresholded pixels (count of "differs from background"
   pixels per row, and per column) to separate the true edge from that bleed: the real boundary is
   where the profile jumps from near-zero to the component's full width/height, not the first
   nonzero pixel. The same profile locates internal features - a divider column, a text run's left
   edge - as a secondary jump inside the outer bounds.

4. **Scale-normalize with a shared anchor.** Two screenshots at different zoom are not comparable
   in raw pixels - this is the step that makes the rest of the comparison valid, and skipping it
   produces numbers that look precise but are not comparable. Pick one element present in both
   images that isn't itself the thing under question - a text label's glyph height is the reliable
   choice, since font rendering doesn't shift with a layout bug. Measure that anchor's height in
   both images (steps 2-3, applied to the anchor instead of the target), then:
   ```
   scale_factor = anchor_height_in_reference_image / anchor_height_in_other_image
   ```
   Multiply every raw-pixel measurement in the "other" image by that factor before comparing it to
   the reference image's numbers. Which image is the reference is a per-task call - usually
   whichever is closer to 1:1 with CSS px (e.g. a browser screenshot at 100% zoom) - decide it and
   state the ratio used. Never report a converted px number without also stating the anchor and
   factor that produced it; both are per-screenshot-pair measurements, not constants this skill can
   supply.

5. **Match the normalized delta to a real token.** Report both bboxes in the same unit plus the
   delta, then check it against the project's own spacing/size scale. `nearest-token` above already
   does nearest-neighbour matching, but only for colors (`--hex`, Euclidean RGB distance) - for a
   spacing/size number, apply the same nearest-neighbour idea by hand against the project's real
   `Spacing`/size constants (grep the theme/tokens file for the target repo) until `nearest-token`
   gains a numeric mode.

### Not built yet

No script in this skill automates bbox thresholding, row/column profiling, or numeric (non-color)
nearest-token matching - `figma_pixel_diff.py` only has `fetch`/`sample`/`crop`/`inspect`/
`nearest-token`, and the last is color-only. Building a `measure` subcommand (threshold + profile +
anchor scale-factor + bbox delta) and a `--value` mode on `nearest-token` (numeric distance instead
of RGB) is a separate decision from documenting the method here.
