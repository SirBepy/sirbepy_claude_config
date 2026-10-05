<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: screenshot/SKILL.md covers capture and the --plan evaluate step covers DOM getBoundingClientRect; neither helps on a canvas-rendered app where there is no DOM box to query -->
# Measuring a rendered box from a screenshot is hand-rolled every time

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/screenshot` (or a sibling helper) a way to measure an element's box geometry from a captured PNG, so verifying a geometric claim on a canvas-rendered app does not mean writing a fresh PIL script each time.

## Context

Surfaced by `/close` Phase 1 on 2026-09-25, in a zng-admin session. The same measurement was hand-written three times in one session, from scratch each time, to answer one question Joe asked directly: are these two boxes the same height.

Why the existing tooling did not cover it:

- `skills/mockup/SKILL.md` and `skills/screenshot/SKILL.md` already mandate measuring a geometric claim rather than eyeballing it, and `screenshot-helper.cjs`'s `--plan` has an `evaluate` step for `getBoundingClientRect()`. That works on a DOM app.
- It does not work on **Flutter web with CanvasKit**, which paints to `<canvas>`. There is no DOM box for a form field, so `getBoundingClientRect` has nothing to query, and the semantics tree exposes labels and rects for interactive nodes only, not for arbitrary decoration.
- `~/.claude/refs/flutter-web-playwright.md` and `feedback_pixel_compare_design_claims` both say to measure pixels, but neither ships a way to do it.

The measurement that actually worked, and the one that did not:

- **Failed:** scanning a single pixel COLUMN for runs of the border colour. Antialiased glyph edges fall inside any sane colour tolerance, so it returns a dozen one-pixel runs and no usable box.
- **Worked:** scanning each pixel ROW for a horizontal run of at least ~60 consecutive border-coloured pixels, then pairing consecutive matching rows into top/bottom edges per x-band. Clean, unambiguous output: boxes at `(1480, 1527)` next to one at `(1480, 1524)`, which is exactly the 48px vs 45px defect being hunted.

```python
from PIL import Image                      # PIL 12.2.0 is installed
im = Image.open(shot).convert('RGB'); px = im.load()
def near(c, t, tol=14): return all(abs(c[i]-t[i]) <= tol for i in range(3))
# per row: collect x-runs of >= MIN_RUN pixels matching the border colour
# then pair consecutive rows within the same x-band into (top, bottom, height)
```

The cost of leaving it: every future geometric verification on a Flutter web surface re-derives this, and the obvious first attempt (column scan) is the one that fails, so each rediscovery burns a round trip. This session burned three.

## Approach

Add a measure mode to `skills/screenshot/screenshot-helper.cjs`, or a small `measure-box.py` beside it, taking an image path, a target colour (hex or a token name), an optional x/y crop window, and a minimum run length. It prints the detected boxes as `(top, bottom, height)` per x-band, plus a pass/fail when given an expected height.

Then reference it from:
- `skills/screenshot/SKILL.md`, next to the existing `evaluate`/`getBoundingClientRect` guidance, with one line saying that path is DOM-only and this is the canvas equivalent.
- `refs/flutter-web-playwright.md`, under the capture gotchas.
- `skills/mockup/SKILL.md`'s "Geometric/numeric claims, measured" bullet.

Do not draft the script inline in this todo; `/bepy-skill-creator` or a normal edit session owns writing it.

## Acceptance

- One command measures a box's height from an existing PNG without writing a new script.
- Running it on a Flutter web screenshot reproduces the 48 vs 45 result described above from the same inputs.
- The three docs named above point at it, so the next session finds it before hand-rolling a column scan.
