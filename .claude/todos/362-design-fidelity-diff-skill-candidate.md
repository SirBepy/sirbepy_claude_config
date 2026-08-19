<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=HARD, worth=6, reconfirm-count=1, content-hash=59a398dc -->
# Skill candidate: render-and-diff a built screen against its design tile

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop hand-rolling the render-measure-compare loop every time a UI ticket needs checking against a
design. It was rebuilt from scratch roughly six times in one zng-app session.

## Context

Session 2026-08-17 (zng-app, share-to-claim epic 54968) shipped four screens. Each one needed the
same loop, and every iteration of it was hand-written from nothing:

1. `flutter build web --release --dart-define-from-file=.env.dev`
2. serve `build/web` via `/supervised-run`
3. drive the flow with Playwright to reach the screen
4. capture screenshots
5. measure the PNG against the design tile
6. read both back and judge

Steps 1-4 are partly covered by the existing `flutter-e2e` skill and zng-app's project-level
`verify` skill. **Steps 5-6 are covered by nothing**, and they are where the value is - four
ad-hoc Python scripts got written mid-session (`C:\tmp\v2-measure\{measure,nav,colours,verify_btn}.py`)
to do band detection, gap measurement, colour sampling and glyph-colour comparison.

Why it matters beyond convenience: without measurement, the fidelity review was done by eye and
**four of eight reported "defects" were not defects at all** - they came from comparing a 430px-wide
capture against a 393pt design frame. The measurement scripts are what caught that. See
`feedback_verify_screenshots_for_defects` in the zng-app project memory.

`figma-pixel-diff` already exists but solves a narrower problem: it fetches ONE Figma node and
matches a sampled colour to the nearest project token. It does not do band/gap measurement, does not
compare against a locally rendered build, and hits the Figma REST API (quota-risky - see
`reference_figma_access_and_quota`).

## Approach

The reusable core is the measurement half, not the driving half - driving is already
project-specific and `flutter-e2e` owns it.

Sketch: a script (Python + Pillow, which was present and worked fine) taking a built screenshot, a
design tile, and the two logical widths, that reports:

- content bands via row-profile scan (rows that are entirely background vs not), giving the exact
  gap between each consecutive block in LOGICAL px on both sides
- left/right ink margins per band, which yields page padding and detects centred vs left-aligned
- ink bounding boxes for named regions, for element sizes and glyph-colour sampling
- a side-by-side table of design vs built with the delta per row

Then either fold it into `flutter-e2e` as a "compare" mode, or make it its own skill that
`flutter-e2e` and `verify` can both call. Decide once the script is generalised - do not design the
skill boundary first.

The four scripts in `C:\tmp\v2-measure\` are the working starting point but are throwaway quality
and hardcode the zng-app tile paths.

**Also fold in the three hard-won gotchas**, which cost most of a session and are currently only in
zng-app's project memory (`reference_enable_semantics_resets_scroll`) even though at least the first
two are true of Flutter web generally:

- `enableSemantics` resets the scroll offset - capture screenshots BEFORE calling it
- a full-page pixel diff gives false passes when a button flashes a loading spinner - clip the CTA bar
- mouse drag never scrolls Flutter web (wheel does), and the semantics overlay swallows wheel events
  until `flt-semantics-host` is removed

## Acceptance

- One invocation produces the design-vs-built delta table; no ad-hoc script written at the call site
- Works from a locally rendered build plus a design PNG, with **no Figma API call**
- The logical-width normalisation is handled explicitly, so a capture width differing from the
  design frame width can never again be misread as a type-size defect
- The three Flutter-web gotchas above are stated in whatever skill file ends up owning the driving
  half

## Notes

Filed from a zng-app session per the CLAUDE.md rule that findings about the global `~/.claude` tree
belong in this backlog, not the surfacing project's. No global files were edited from that session.
