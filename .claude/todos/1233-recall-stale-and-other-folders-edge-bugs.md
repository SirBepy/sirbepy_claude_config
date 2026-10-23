<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 02 shares only the words recall/memory/repo -->
# recall memory --stale-days crashes on a bad date; other_folders hides a prefix-sharing sibling repo

**Type:** bug
**Origin:** ai

## Goal

Two edge bugs from cycle-1 code are fixed with tests.

## Context

Found by the 2026-10-23 loop-todos cycle-1 `/code-check` over `8347382..HEAD`.

1. `skills/recall/recall.py` `cmd_memory_stale`: `day()` checks only the date shape, so frontmatter
   `verified: 2026-13-45` makes `strptime` raise and the whole stale listing crashes.
2. `skills/clockify-reconciliator/scripts/other_folders.cjs` `isConfiguredFolder`:
   `name.startsWith(s + '-')`, meant for worktree suffixes, also treats a sibling repo like
   `zng-app-x` as configured `zng-app`, hiding its activity from the negative-evidence list. The
   test uses zng-app and zng-api, which do not collide; `render()` and its NOTE line have no test.

## Approach

1. Catch the ValueError and label the file "bad verified date" instead of crashing.
2. Match worktree suffixes by the real worktree naming pattern only, or check the folder against the
   configured repo's `git worktree list`.

Add a case to `skills/recall/test_recall.py` and `skills/clockify-reconciliator/scripts/test_other_folders.cjs`.

## Acceptance

Both new tests fail before the fix and pass after it.
