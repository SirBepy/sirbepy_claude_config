<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# bundle-board.mjs escapes inlined CSS with a JS-only escape

**Type:** bug
**Origin:** ai

## Goal

Inlined stylesheet text renders unchanged after `bundle-board.mjs` bundles a board.

## Context

Found by the 2026-10-23 loop-todos cycle-1 `/code-check` over `8347382..HEAD`.
`skills/mockup/bundle-board.mjs:111-114` `escapeInline` rewrites `<` as `\x3C` for scripts and
styles alike. `\x` is not a CSS escape, so a stylesheet containing `</body>` or `<!--` (e.g. in a
`content:` string) renders as the letter x plus 3C, and a literal `</style` is not escaped at all.
Rare, but silent.

## Approach

Use a CSS escape (`\3C ` with a trailing space) on the style branch and also handle `</style`, or
reject those literals in CSS with a clear error. Add a case to `skills/mockup/test_board_scripts.cjs`.

## Acceptance

A board whose CSS contains `content: "</body>"` renders that string unchanged after bundling, and
`</style` inside CSS cannot break out of the style element.
