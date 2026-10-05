# Degraded asset production

Used two ways: as the prompt handed to a fresh `general-purpose` subagent
when the harness has a subagent tool but no agent type registered under the
name `impeccable-asset-producer`, or followed in-thread on a harness with no
subagent tool at all.

## Inputs

The approved comp, output paths, required dimensions and formats,
transparency needs, crop notes, and the list of what must remain semantic
code rather than a raster.

## What to do

1. For each required asset, decide the medium first: a crop straight from
   the approved comp, a native image tool if the harness has one, or
   `generate-image.mjs` (`node .claude/skills/impeccable/scripts/generate-image.mjs --prompt "<prompt>" --out <path> [--size WxH] [--quality medium]`,
   or `--prompt-file <path>` for a long prompt). Never rasterize anything the
   input list marks as semantic code - a button, a heading, body text.
2. Match the required dimensions, format, and transparency exactly; a
   near-size asset forces a second round through the same list.
3. After generating with any tool, run
   `node .claude/skills/impeccable/scripts/embed-prompt.mjs <image> --prompt "<the prompt used>"`
   so the intent survives the file leaving this session (`generate-image.mjs`
   does this automatically; a native tool or a straight crop does not, so
   embed it by hand).
4. Write each output to the exact path given. An asset the caller cannot
   find at the path it asked for is an asset that was not produced.

## Degraded disclosure

One line in the caller's final report:
`⚠️ DEGRADED: asset production ran via <general-purpose agent|in-thread pass> (no impeccable-asset-producer agent type on this harness)`.
