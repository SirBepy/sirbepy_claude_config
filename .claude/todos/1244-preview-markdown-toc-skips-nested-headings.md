<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1242 (done) was the phone layout; no backlog file covers render_markdown's toc_tokens walk -->
# /preview markdown renderer lists only top-level headings and leaves nested heading ids un-namespaced

**Type:** bug
**Origin:** ai

## Goal

`skills/preview/render_markdown.py` puts every H2/H3 of a doc in the nav, and namespaces every
heading id with the doc slug, including docs that open with an H1.

## Context

Found 2026-10-24 by the todo 1242 builder (loop-todos run). `build_page` walks only the top level
of `md.toc_tokens`. Python-Markdown nests tokens by level, so a doc that starts with an H1 (nearly
every real doc) has all its H2/H3 as `children` of that one H1 token: the nav lists the H1 alone,
and the id-namespacing loop rewrites only the H1's id, so two docs on one page that share an H2
title (e.g. "Overview") still collide on `id="overview"`. The builder's multi-doc test used docs
with no leading H1 to stay clear of it. Related oddity, same code: a `#<heading-id>` deep link
fails the doc lookup on load and falls back to the first doc.

## Approach

Flatten `toc_tokens` recursively (depth-first) before both the nav loop and the id-rewrite loop,
keeping the existing `level <= 3` filter for the nav. Optionally resolve a heading-id hash on load
to its containing doc.

## Acceptance

- A test in `skills/preview/test_render_markdown.py` with an H1-led doc shows its H2s in the nav
  and two such docs sharing an H2 title get distinct ids; it fails against the current renderer.
