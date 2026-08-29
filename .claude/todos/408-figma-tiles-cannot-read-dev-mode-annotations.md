<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=7, reconfirm-count=2, content-hash=719a4cf3 -->
<!-- duplicate-checked -->
# `figma-tiles` cannot read Dev Mode annotations, and its depth rule hides them

**Type:** skill-improvement
**Origin:** ai

## Goal

Let `figma-tiles` pull **Dev Mode annotations** alongside tiles and comments, and correct the depth
guidance that currently makes them unreachable.

## Context

Follow-on from todo **386** (the "unmetered" claim), which is now in `done/`. This is the larger gap
found the same day and is not covered by it.

`figma-tiles` sweeps tiles and comments. **Dev Mode annotations are neither.** They are an
`annotations` field on the node itself, never returned by `/comments`, and they carry the
interaction rules that screenshots cannot show: what opens a bottom sheet, what must persist across
Back, which controls must appear together, which inputs are read-only rather than disabled.

They hang off nested nodes, so the skill's `depth=3` cap misses nearly all of them. Measured on
`fYPW2rFITwhf4WqvkUy9zN` on 2026-08-19: the depth-3 section sweep surfaced **3**; fetching each
frame individually at `depth=10` surfaced **52**. One of those 52 identified a live bug in shipped
zng-app code (an input styled as disabled where the design says read-only).

**This also disproves the skill's framing of depth as the danger.** 220 frames fetched as
`nodes?ids=<5 ids>&depth=10`, 44 batches 6s apart: **zero rate limiting, every call 200**. The
2026-08-12 lockout was a whole *page* at depth 6. Tree size is the cost driver, not depth. Per-frame
deep reads are cheap; per-page deep reads are not.

## Approach

1. Add an `annotations` subcommand beside `sweep` and `comments`, taking the frame ids `sweep`
   already resolved, so it costs nothing extra to run straight after one.
2. Lift the working implementation rather than rewriting it:
   `zng-app/.for_bepy/figma/tiles_aug26/fetch_annotations.py` (batched fetch, walks the tree for the
   `annotations` field) and `merge_annotations.py` (flattens the Quill HTML labels into readable
   markdown and dedupes annotations repeated across sibling frames).
3. Rewrite the depth guidance in `SKILL.md` to distinguish per-frame from per-page reads, instead of
   banning depth outright. Keep the per-page ban.
4. Batch size 5 with a ~6s gap is what was measured as safe; keep it conservative rather than tuning
   for speed.

## Acceptance

- A sweep can be followed by an annotations pass with no hand-rolled script.
- The output is readable markdown, one entry per distinct annotation, deduped.
- `SKILL.md` no longer implies depth alone is the cost driver, and still forbids whole-page depth.

## Notes

- Annotation labels arrive as Quill HTML (`<p>`, `<li value="1" data-list="bullet">`, inline styles),
  not plain text or markdown. Rendering them raw is unreadable.
- The same annotation repeats across sibling frames; dedupe on the label text, not the node id.
