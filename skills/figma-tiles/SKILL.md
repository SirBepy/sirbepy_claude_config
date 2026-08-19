---
name: figma-tiles
description: Turns a Figma board into per-screen tiles and a comment digest, rate-limit safe, with an offline export fallback.
argument-hint: "<figma-url-or-file-key> <section-node-id...>"
---

# /figma-tiles

> Turn a Figma board section into per-screen tiles and a comment digest, without redoing the quota work from scratch.

## Quota rules (read before running anything)

Figma's REST API bills by tree size, not node count. A whole-page read at depth 6 has produced
`Retry-After` values past 100 hours on `/v1/files` and `/v1/images` separately - they are
different budgets, both exhaustible independently. The rules below are enforced by
`skills/_shared/figma_client.py`, not left to memory:

- Tree fetches are always scoped to a specific section/node id, never a whole file, and capped at
  `depth=3` unless you pass `force=True` in code (the CLI has no flag for this on purpose).
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
batch - do not paste every tile inline into one context window.
