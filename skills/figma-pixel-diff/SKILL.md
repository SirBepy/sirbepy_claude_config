---
name: figma-pixel-diff
description: Fetches one Figma node, samples/crops its rendered PNG, and matches a pixel color to the nearest project token.
argument-hint: "<figma-url-or-node-id>"
---

# /figma-pixel-diff

> Verify one Figma detail against an implementation: exact color, copy text, or layout, without
> hand-rolling PowerShell/Python one-liners each session.

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
