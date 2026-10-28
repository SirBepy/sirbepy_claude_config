<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Skill candidate: render and screenshot HTML comps with headless Chrome

**Type:** skill-improvement
**Origin:** ai

## Goal

Package the "build an HTML comp, screenshot it, look at it" loop that got hand-rolled five-plus
times in one session, including the two traps that produced false defect reports.

## Context

Observed 2026-08-10 in hubbub-game-music-guesser. The loop was rebuilt from scratch for: four
direction comps, four cassette variants, three lettering options, the album-colour probe, and
finally the real React components. Every round re-derived the same scaffolding, and two rounds
produced wrong conclusions from correct code.

The existing `/screenshot` skill is for portfolio shots of a running app. This is a different
job: render local static or bundled HTML and inspect it.

The recurring pieces:

- `chrome --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1
  --user-data-dir=<scratch> --window-size=W,H --screenshot=<abs path> <file:// url>`
- The output path must be **absolute**. A relative `--screenshot` silently writes nothing while
  the command still reports success.
- `body:has(section:target) section:not(:target) { display:none }` plus `#id` in the URL, to
  isolate one panel of a multi-panel comp for a legible capture.
- `--virtual-time-budget` to let effects and fetches settle before the shot.
- Bundling real components for capture: esbuild IIFE, `jsx: "automatic"`,
  `loader: { ".woff2": "dataurl", ".woff": "dataurl" }`, and a linked `bundle.css`.

The two traps, both of which cost real time:

1. **Sub-500px window sizes are a lie on Windows.** Chrome clamps the window to ~500px wide, so
   `--window-size=390,844` renders a 500px page and crops it to 390. Correct layouts look broken.
   Fix: wrap the page in a `<iframe width=390 height=844>` on a wrapper page and shoot that.
2. **`--virtual-time-budget` catches CSS transitions mid-flight.** A staggered fade-in rendered
   at 40% opacity read as clipped text. Fix: measure the DOM before believing a visual defect.

Both are now recorded in the vault under `Claude Code.md`.

## Approach

Build a `/comp-shot` skill wrapping:

1. `render <html-or-entry> [--w --h] [--panel <id>] [--phone]` - resolves Chrome, forces an
   absolute output path, applies the iframe wrapper whenever width < 500, waits out virtual time.
2. `bundle <entry.tsx>` - the esbuild config above, for shooting real components against a
   fixture instead of a hand-made lookalike.
3. A `measure <selector>` mode that dumps `getBoundingClientRect()` and `innerWidth`, so
   "is this actually broken" is one command rather than an improvised debug page.

Sanity-check first whether `/screenshot`'s Playwright helper should absorb this instead of a new
skill; Playwright has no 500px clamp and would remove trap 1 entirely. That may be the better
answer, in which case this todo becomes "extend `/screenshot` with a static-HTML mode".

## Acceptance

- A capture of a multi-panel comp at desktop and phone widths takes one command per view.
- The phone capture is genuinely 390px wide, verified by an in-page `innerWidth` readout.

## Notes

Working reference implementation to lift from, before it is deleted as scratch:
`hubbub-game-music-guesser/.impeccable/comp/harness/build.mjs` (esbuild config, page template)
and `phone.html` (the iframe wrapper).
- Duplicate of 63 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
