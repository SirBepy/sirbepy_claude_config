<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1188 (done) built these scripts; this is the follow-up dedupe found by code-check -->
# mockup bundle-board and verify-board duplicate vite resolution and the literal lint

**Type:** refactor
**Origin:** ai

## Goal

One shared helper owns vite ESM-entry resolution and the `</body>`/`<head`/`<html` literal lint.

## Context

Found by the 2026-10-23 loop-todos cycle-1 `/code-check` over `8347382..HEAD`.
`skills/mockup/bundle-board.mjs:31-39` and `:101-118` vs `skills/mockup/verify-board.cjs:94-99` and
`:73-86`: the `pkg.exports['.'].import` resolution is copied verbatim and the script/style/comment
literal scan is implemented twice.

## Approach

Extract `skills/mockup/_board-lib.cjs` (require()-able from the .mjs) with `resolveViteEsm` and
`lintLiterals`. `test_board_scripts.cjs` SKIPs without `BOARD_PROJECT`, so run it with that env set
(a repo with vite installed, e.g. claude_usage_in_taskbar) as the exercise test.

## Acceptance

Both scripts import the shared helper, and
`BOARD_PROJECT=<repo with vite> node skills/mockup/test_board_scripts.cjs` passes.
