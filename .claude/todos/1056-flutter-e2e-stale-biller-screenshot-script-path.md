<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 314 is done/ and added the login preamble itself; 221/293/935/1010 are other skills' stale paths, different surfaces -->
# flutter-e2e SKILL.md points at a zng-biller script path that no longer exists

**Type:** task
**Origin:** ai
**Created:** 2026-09-30

## Goal

Stop `/flutter-e2e` sending sessions to `scripts/screenshot-dev.js` in zng-biller, which is no longer
tracked there.

## Context

`skills/flutter-e2e/SKILL.md:48` (Login preamble, fast path) says "zng-biller's committed reference
implementation: `scripts/screenshot-dev.js`". On 2026-09-30 Joe had that script untracked from
zng-biller (commit c6641ea) and moved to the gitignored `.for_bepy/screenshot-dev.js`, to match
zng-app's rule: a real e2e suite is tracked (`zng-app/e2e/`), one-off Claude verification scripts
are not (`zng-app/e2e/.gitignore` ignores `verify-*`, `repro-*`, `shot-*` and similar).

## Approach

Replace the pointer with the local-only path, or point at zng-app's tracked `e2e/lib/auth.js`
(`bootAuthedTo`) as the committed reference and mention biller's local copy as secondary.

## Acceptance

- No mention of `scripts/screenshot-dev.js` as a committed file remains in `skills/flutter-e2e/SKILL.md`.
