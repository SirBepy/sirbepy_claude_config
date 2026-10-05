<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=EASY, worth=8, reconfirm-count=1, content-hash=10d86318 -->
<!-- duplicate-checked: 1026 (done) is about SKILL.md telling callers to `git add` new files first; 983 (done) is the coverage check missing a forgotten source-deletion half. Neither covers a directory pathspec silently skipping new files inside an already-tracked directory. -->
# commit-pathspec.sh silently drops new untracked files inside an already-tracked directory pathspec

**Type:** skill-improvement
**Origin:** ai

## Goal
When a commit pathspec names a directory, every untracked file under it lands in the commit (or the script refuses and names them), instead of the commit silently containing only the tracked changes.

## Context
2026-10-05, mc_plugins_tag session (shop/Market plugin). `bash ~/.claude/skills/commit/commit-pathspec.sh ... -- market server/market-prices ...`:
- Earlier the same day, `-- market` with `market/` entirely untracked committed every file (2b23bb0).
- Later, `-- market` with `market/` already tracked plus four NEW files inside it (`PriceBook.java`, `PriceCommand.java`, `prices.yml`, `PriceBookTest.java`) produced commit 119a02c containing only the tracked modifications. The new files stayed `??` and the script printed `[commit] committed` with no warning, so HEAD referenced classes that weren't in the commit. Caught only because `git status` was read afterwards; folded via auto-commit.md Case A into e4a4e69.
- `server/market-prices` (a wholly new directory) in that same pathspec WAS included, so the gap is specifically "tracked directory + new files inside it".
UNVERIFIED, would check `skills/commit/commit-pathspec.sh`'s classification loop: the pathspec classification (`[pathspec] classification:` printed an empty list) expands untracked entries only for paths that are themselves untracked, and `git commit -- <dir>` never adds untracked files.

## Approach
In `skills/commit/commit-pathspec.sh`, for each pathspec entry that is a directory, list `git ls-files --others --exclude-standard -- <dir>` and treat those files as untracked entries (stage them after the checks, like a named new file). Add a test under the script's test suite that commits a tracked dir with one modified and one new file and asserts both land.

## Acceptance
- The reproduction above commits all four new files, or refuses naming them.
- The commit skill's tests pass.

## Notes

- Done in loop-todos cycle 2 (2026-10-06): commit-pathspec.sh expands an already-tracked directory pathspec with git ls-files --others --exclude-standard, so new files inside it are classified untracked and committed; wholly-untracked dirs keep the old path. r31 RED then GREEN, r32 guards the untracked-dir case; suite 69/69.
