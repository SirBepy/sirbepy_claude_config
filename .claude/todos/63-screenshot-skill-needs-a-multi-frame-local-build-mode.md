<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=6, reconfirm-count=2, content-hash=a26db69c -->
# /screenshot needs a multi-frame mode; design sessions keep hand-rolling the same Playwright harness

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `~/.claude/skills/screenshot/` a mode that shoots N parameterised frames of a local page in
one run, so design sessions stop writing the same 40-line Playwright script every time.

## Context

Written on 2026-08-09 after a Split Opinions redesign session in
`hubbub-game-split-opinions` where I wrote **three** near-identical harnesses in one sitting:

1. `.for_bepy/original-look/shoot.cjs` - 10 frames of a static recreation, `file://`, two viewports.
2. `.for_bepy/comps/` shooting - 6 design comps plus a contact sheet, same shape.
3. `.for_bepy/preview/shoot.cjs` - 18 frames of a React build, needing a throwaway static server
   because ES modules will not load over `file://`.

Each one independently re-derived the same things: launch chromium, loop a list of
`[name, query, width, height, waitMs]`, set `deviceScaleFactor` per device class, capture
`pageerror` so a blank render fails loudly instead of silently, screenshot, close context.

Each also hardcoded the same brittle path, copied out of the existing helper:

```
require("C:/Users/tecno/AppData/Local/npm-cache/_npx/e41f203b7505f1fb/node_modules/playwright")
```

The existing `screenshot-helper.cjs` does not cover this: it is built for portfolio-quality shots
of one page, not a matrix of states. The matrix case is the normal one for any design or redesign
work, which is exactly when `/impeccable` says the screenshot round is non-skippable.

## Approach

Extend `screenshot-helper.cjs` (or add a sibling) taking a frame list and an output dir:

- frames as `{ name, url | query, width, height, wait }`, defaulting `deviceScaleFactor` by width
- resolve the playwright install once, in the helper, instead of every caller pasting the npx path
- optionally serve a directory on an ephemeral port and tear it down in the same process, since
  the module case needs it and every caller currently reinvents it
- fail non-zero on any `pageerror`, so a blank page cannot pass as a successful shot

Then note the mode in `SKILL.md`'s description surface so it fires for "shoot every state of this
component", not only for portfolio shots.

## Acceptance

- One command shoots a named frame matrix of a local page, static or bundled, into a given folder.
- No caller needs to know where playwright is installed.
- The existing portfolio flow still works unchanged.

## Merged in (2026-08-11)

Absorbed todos 44, 72, 236 during /cleanup-todos. Their full text is in `done/` - read them before implementing, they carry specifics this file does not.
