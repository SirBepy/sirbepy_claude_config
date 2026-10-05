<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1035 is about hardcoding "Joe" in skill prose, 997 is about generating the calendar and caching the hubstaff token - both distinct from this visual-critique-followup list, only sharing "clockify/week/preview" vocabulary -->
# clockify-week preview: unaddressed P2/P3 findings from the 2026-09-28 impeccable critique

**Type:** task
**Origin:** ai

## Goal

Apply (or explicitly decline) the P2/P3 findings from the 2026-09-28 dual-agent impeccable
critique of `skills/clockify-reconciliator/scripts/render_week.cjs` that were surfaced but never
picked up - Joe moved on to a different set of issues he found live in the preview panel (dashed
"other project" box confusion, hour-label format, a real gutter-alignment bug) and those got fixed
instead; the original critique's P2/P3 list was offered once and never revisited.

## Context

Full write-up: `C:\Users\tecno\.claude\.impeccable\critique\2026-09-28T14-19-17Z__lls-clockify-reconciliator-scripts-render-week-cjs.md`.
The two P1s from that critique (sticky gutter, description line-clamp) WERE applied and committed
(`0a8a7b1`). These four were not:

- **Sub-14px blocks render as blank colored slivers.** A block under ~14px shows no time/desc at
  all (by design, per `render_week.cjs`'s own height-tier comment), but a fully blank div is
  indistinguishable from a rendering bug. Proposed fix from the critique: keep a 1-character glyph
  (e.g. a centered dot) at any height >= 8px.
- **Near-invisible column dividers, no horizontal hour gridlines.** `.v2-col { border-left:1px
  solid #191d24; }` against `#0f1115`/`#12151b` is roughly 1.2:1 contrast. Tracing a block back to
  its hour in the 5th-7th day column means eyeballing an unmarked line across most of the card's
  width. Proposed fix: a repeating background-gradient on `.v2-colbody` matching `HOUR_PX` (34px),
  plus a brighter `.v2-col` border color.
- **"Logged" (`.chip-old`) has no accent color anywhere**, unlike `.chip-new`/`.chip-edit`/
  `.chip-meeting`, which each tint to match their block's color. It's also the LARGEST category by
  volume most weeks, so the biggest chunk of the week reads as unstyled default text. Proposed:
  `.chip-old { color: #8fd6ab; }` (a lighter tint of the existing `.sw-old`/`.v2-old` green
  `#3f7a56`).
- **Type scale compressed to a 9-15px band, no real modular scale** (detector-flagged,
  `flat-type-hierarchy`, ratio 1.7:1, corroborated independently by both critique assessments).
  Not necessarily wrong for a dense report card, but never deliberately revisited.

A separate P3 (empty Sat/Sun columns look identical to "data didn't load", no `-` vs. hatching
distinction) was discussed live with Joe on 2026-09-28 in the context of a partial in-progress
week, but no decision was made either way - it's a candidate for this same todo, not yet actioned.

## Approach

Each fix is small and independent - apply them one at a time to
`skills/clockify-reconciliator/scripts/render_week.cjs`, regenerate a sample week with
`render_week.cjs` against real (not fabricated - see `feedback_real_empty_state_over_demo_content.md`
in zng-app's memory for why that matters) entries data, and show Joe the result via `show_preview`
before considering any of them done - none of this needs Joe's sign-off up front, but the visual
result does, per this session's own back-and-forth pattern.

## Acceptance

- Sub-14px blocks show at least a visible glyph, not a blank div.
- Column dividers and/or hour gridlines are visibly distinguishable at normal viewing distance.
- `.chip-old` has a non-default accent color.
- Joe has seen and approved (or explicitly declined) each change live in the preview panel.

## Notes

Joe's own priority call on this list is unknown - ask before batching all four into one session,
since he may only want a subset (same pattern as the P1-only pick earlier in this same session).
