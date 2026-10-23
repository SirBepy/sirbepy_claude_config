<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# build_gallery.py forms the preview render URL twice and lets manifest ids collide

**Type:** refactor
**Origin:** ai

## Goal

One `render_url(id)` helper builds the preview-render URL, and manifest section ids never collide.

## Context

Found by the 2026-10-23 loop-todos cycle-1 `/code-check` over `8347382..HEAD`.
`skills/preview/build_gallery.py:508` (the `--check` path, untested) and `:295-304`
(`render_url_from_response`) both build `f"{RENDER_CHECK_ENDPOINT.rstrip('/')}/{id}"`. Same review:
section ids come from `slugify(item id)` with no uniqueness check, so two manifest ids can collide as
HTML ids, and the dropped-items follow-up never converges when one item alone exceeds the budget.

## Approach

Add `render_url(id)` and use it at both sites; dedupe section ids with a suffix on collision; make
an over-budget single item a clear error. Extend `skills/preview/test_build_gallery.py`.

## Acceptance

Both call sites use the helper; tests cover duplicate ids and a single over-budget item.
