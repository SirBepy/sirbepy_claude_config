---
name: e2e
description: Runs a project's browser/app-driven end-to-end suite by delegating to /flutter-e2e or /jest-lua, or render-and-diffs a built screenshot against a design tile for fidelity checking.
disable-model-invocation: true
argument-hint: "[flow description | test-plan.md path] | diff --built <png> --built-width N --design <png> --design-width N"
---

# /e2e

> Browser/app-driven end-to-end runs, stack inferred and delegated - plus a design-fidelity diff
> mode so nobody hand-rolls a measurement script again.

Split out of `/test` on 2026-08-19: `/test` stays fast-checks-only, this owns everything that
drives a real UI. Two independent modes, pick by what's asked.

## Mode A - Run (default)

Delegates entirely; this skill never reimplements a driver.

| Marker at repo root | Stack | Delegate |
|---|---|---|
| `pubspec.yaml` with a `flutter:` dependency | Flutter | `/flutter-e2e` - scripted mode for a flow description, plan-file mode for a `.md` test-plan path |
| `test.project.json`, `*.rbxlx`, or a `testing/wally.toml` | Roblox / Luau | `/jest-lua run` (its `run-in-roblox` fallback is the client-in-the-loop path for this stack) |
| `package.json` with a Playwright config or `snippets/test-e2e.md` import | Node / web | follow `~/.claude/snippets/test-e2e.md` exactly - affected-specs by default, full suite when asked, dispatched to a background subagent |
| anything else (bare Node without Playwright, Rust/Tauri) | - | no scripted e2e path exists - ask "how would I observe this if I had no test suite at all?" and drive/inspect the real system by hand instead of reporting a dead end |

State the detected stack and the exact delegate before driving anything.

## Mode B - Diff (design fidelity)

Trigger: `diff` as the first argument, or a `--built`/`--design` pair given directly.

Renders and measures a locally captured screenshot against a design tile - band/gap positions, ink
margins, pixel colors - so a fidelity review has numbers instead of eyeballing. **No Figma API
call, ever**; both images must already exist on disk (a build already run through `/flutter-e2e` or
equivalent, and a design PNG already exported or fetched by `figma-tiles`/`figma-pixel-diff`).

Filed from a zng-app session where the same measure-and-compare loop was hand-written from scratch
six times; four of eight "defects" it caught weren't real, they came from comparing a 430px capture
against a 393pt design frame - see the logical-width step below.

### Workflow

1. **Capture correctly first.** If the built screenshot doesn't exist yet, read `/flutter-e2e`'s
   "Capture gotchas" section before driving the shot - clipping/scroll/wheel traps there apply to
   this mode too, since a bad capture makes every measurement downstream wrong regardless of tool.
2. **Know both logical widths.** The design frame's width is whatever units the export states
   (Figma frame width in points). The built capture's logical width is the Playwright viewport
   width used to take the shot, NOT the PNG's pixel width - a 2x DPR shot of a 393pt viewport is a
   786px PNG. Passing the wrong one is exactly the bug this tool exists to prevent; `compare` warns
   loudly if the two logical widths you pass differ, since that usually means one of them is wrong.
3. **Run the comparison:**
   ```
   python skills/e2e/scripts/design_diff.py compare \
     --design <design_tile.png> --design-width <points> \
     --built <built_screenshot.png> --built-width <points> \
     --tol 12
   ```
   Reports, in logical px for both images: content bands (row-profile scan of rows that are
   entirely background vs not), the gap above each band, and left/right ink margins per band -
   read margins for centred-vs-left-aligned and page padding. Bump `--tol` (default 12, an RGB sum-
   of-diffs threshold) if antialiasing on a gradient background creates phantom bands.
4. **Clip a flashing region before banding**, e.g. a CTA that may show a loading spinner:
   `--exclude-built 700,760` (repeatable, logical y-range) blanks that band to background before
   the scan, so a spinner frame can't fake a "different" delta.
5. **Zoom into one element** with `ink-box` (bounding box + fill/corner color, for button/icon
   geometry and rounded-vs-square corners) or `sample` (raw pixel color at a logical x,y) - both
   take the same `--logical-width` normalization as `compare`.
6. **Judge from the delta table**, not the raw numbers alone: a height/gap delta under ~1-2 logical
   px is antialiasing noise, not a defect. A band-count mismatch between design and built means the
   two aren't even structurally aligned - fix that before trusting any row-matched delta.

### Script reference

`skills/e2e/scripts/design_diff.py` - `bands` (single image), `compare` (design vs built delta),
`ink-box` (bounding box + fill/corner sample), `sample` (raw pixel color). Run any subcommand with
`-h` for its exact flags. Pure PNG math (PIL + numpy), no network access.

## Acceptance checklist

- [ ] Mode picked matches the ask - a flow/plan-file drives, `diff`/`--built`+`--design` measures
- [ ] Run mode: delegated, never redrove a flow inline
- [ ] Diff mode: both `--*-width` values are logical/points, not raw PNG pixel width
- [ ] Diff mode: no Figma API call made
- [ ] Diff mode: capture gotchas (semantics/scroll, CTA flash, wheel-scroll) checked before trusting
      a screenshot that showed a surprising delta

## Related

- `~/.claude/skills/flutter-e2e/SKILL.md` - the Flutter driving mechanics and capture gotchas this
  mode's diff workflow assumes were followed.
- `~/.claude/skills/jest-lua/SKILL.md`, `~/.claude/snippets/test-e2e.md` - the other run-mode
  delegates.
- `~/.claude/skills/figma-pixel-diff/SKILL.md`, `~/.claude/skills/figma-tiles/SKILL.md` - where a
  design tile PNG comes from when one isn't already on disk (both hit the Figma API; this skill
  never does).
- `~/.claude/skills/test/SKILL.md` - the fast-checks sibling this was split out of.
