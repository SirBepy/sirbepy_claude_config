---
name: figma-tiles
description: Turns a Figma board into per-screen tiles and a comment digest, rate-limit safe, with an offline export fallback.
argument-hint: "<figma-url-or-file-key> <section-node-id...>"
---

# /figma-tiles

> Turn a Figma board section into per-screen tiles and a comment digest, without redoing the quota work from scratch.

## Quota rules (read before running anything)

Figma's REST API bills by tree size, not depth in isolation. A whole-**page** read at depth 6 has
produced `Retry-After` values past 100 hours on `/v1/files` and `/v1/images` separately - they are
different budgets, both exhaustible independently. That is the read this section still bans. A
scoped per-**frame** read is a different cost profile: 220 frames fetched one at a time at
depth=10, in 44 batches of 5 ids 6s apart, produced zero rate limiting (every call 200; measured
2026-08-19 on `fYPW2rFITwhf4WqvkUy9zN`). Depth alone is not the cost driver - tree size is, and a
whole page is orders of magnitude bigger than one frame at the same depth. The rules below are
enforced by `skills/_shared/figma_client.py`, not left to memory:

- Tree fetches are always scoped to a specific section/node id, never a whole file. `sweep`'s own
  walk is capped at `depth=3` unless you pass `force=True` in code (the CLI has no flag for this on
  purpose) - it can cover an entire section in one call, so it stays shallow. The `annotations`
  command below is the case where a deeper per-frame read is fine: see that section.
- Every fetch (tree, images, comments) is cached to disk under `--cache-dir`. Always pass one and
  reuse it across re-runs of the same board - a cache hit costs zero quota. Without `--cache-dir`,
  only image renders are cached (by filename in `--out`); tree and comment fetches are not.
- On a 429, the client backs off honoring `Retry-After` for up to 8 attempts, then raises instead
  of spinning forever. If that happens, stop and use the `slice` fallback below.
- **Desktop MCP alternative:** the Figma desktop app's Dev Mode MCP server (`127.0.0.1:3845`) is
  metered too - 200 tool calls/day + 10-15/min on a Starter/Pro Dev or Full seat, 600/day + 20/min
  on Organization (`whoami`, `add_code_connect_map`, `generate_figma_design` exempt). See
  https://developers.figma.com/docs/figma-mcp-server/rate-limits-access/. It is also
  selection-driven - it can inspect whatever is selected in the open file, not sweep a whole
  board. Use it for a single screen, not this skill's job. Whether its daily budget shares a
  bucket with the REST API quota above is not documented and not verified here - do not assume
  either way.
- Figma also documents a remote MCP server at `https://mcp.figma.com/mcp`, available on all
  plans. Whether it is node-id addressable (and so usable unattended, unlike the selection-driven
  desktop one) is unverified - check before relying on it.

## Setup

Set `FIGMA_TOKEN` as an environment variable (or add `FIGMA_TOKEN=<token>` to `~/.claude/.env`,
already gitignored). Generate a personal access token at figma.com > Settings > Personal access
tokens. Never hardcode a token in a script or commit one.

## Primary path - the API is available

```
python skills/figma-tiles/scripts/figma_tiles.py sweep \
  --file-key <url-or-key> --section <node-id-or-share-url...> \
  --out <tile-dir> --cache-dir <persistent-cache-dir>
```

One command: resolves each section, finds phone-shaped screen frames (FRAME/COMPONENT/INSTANCE,
300-500px wide, 400px+ tall - override with `--min-w/--max-w/--min-h` for a different device
class), renders each at scale 2 via `/v1/images`, fetches comments and anchors them per screen,
and writes `manifest.json` + `comments.md` into `--out`. Re-running skips PNGs already on disk and
tree/comment fetches already in `--cache-dir`.

## Dev Mode annotations - after a sweep

Comments and annotations are different Figma primitives. Annotations hang off the node's own
`annotations` field, nested under the frame, never returned by `/v1/files/{key}/comments`; they
carry the interaction rules a screenshot can't show (what opens a bottom sheet, what must persist
across Back, which inputs are read-only rather than disabled).

```
python skills/figma-tiles/scripts/figma_annotations.py \
  --file-key <url-or-key> --manifest <tile-dir>/manifest.json \
  --out <tile-dir>/annotations.md --cache-dir <persistent-cache-dir>
```

Reuses the frame ids `sweep` already resolved by reading them straight out of `manifest.json`
(pass `--ids <id1,id2,...>` instead if you don't have one). Fetches 5 frames per request at
depth=10 with a 6s gap between batches - the measured-safe values above, kept conservative rather
than tuned for speed - flattens the Quill HTML labels into markdown, and dedupes repeats across
sibling frames by label text rather than node id, since the same annotation is attached to every
sibling that shares a component.

## Fallback path - API unavailable or rate-limited

Have the dev export the section as a PNG from the Figma desktop app (right-click section > Export,
or select and use the export panel), then slice it locally, no API calls at all:

```
python skills/figma-tiles/scripts/figma_tiles.py slice \
  --export <exported-section.png> --slug <name> --out <tile-dir>
```

Detects screens by masking against the sampled canvas color, trims the section's own outline
first (otherwise it bridges every row/column into one box), splits recursively alternating rows
and columns (connector arrows defeat a naive single-axis projection), upscales tiles under 500px
wide by 2x, and cuts tall scroll mockups into overlapping 1750px strips.

Comments still need the API regardless of which image path was used - a manual export has no
comment data:

```
python skills/figma-tiles/scripts/figma_tiles.py comments --file-key <url-or-key> --out comments.md --cache-dir <cache-dir>
```

## After tiles exist

Fan subagents out over the tile files for screen-by-screen review, one subagent per tile or small
batch - do not paste every tile inline into one context window. Paste the canonical preamble from
`refs/builder-preamble.md` into each dispatch prompt (it's read-only, so the `READ-ONLY DISPATCH`
opt-out applies) - `hooks/dispatch-preamble-guard.py` rejects a prompt missing its markers.
