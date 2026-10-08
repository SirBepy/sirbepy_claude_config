<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=HARD, worth=7, reconfirm-count=1, content-hash=fa96379a -->
<!-- duplicate-checked: 1138 is coverage-tests vs verify probes, 1141 is rm --cached paths; this is own-range derivation for a directory pathspec -->
# commit-pathspec.sh: a directory in the pathspec gets one merged own-range across all its files

**Type:** skill-improvement
**Origin:** ai

## Goal
`skills/commit/commit-pathspec.sh` should derive (or require) own-ranges per FILE when the
pathspec names a directory, instead of treating the directory as one file.

## Context
Seen 2026-10-08 in mc_plugins_tag (session 3f80, floating Dragon Balls commit). The pathspec was
`-- docs/dragonballs.md dragonballs e2e/...` with `--own-range <file>:1-100000` for every changed
file. The `[own-range] derivation` step printed one line for the bare `dragonballs` entry,
"auto-derived own-range 1-11,14-23,39-45,...,340-350 (every current hunk assumed own)", i.e. the
`@@` ranges of ~25 different files concatenated under one key. `[foreign-hunk-check]` then
REFUSED with `dragonballs: foreign-hunks-inside-your-hunk 585-591,347-441 foreign-hunks-present
330-335`: line numbers from different files compared against each other. Every hunk was this
session's own. Passing each changed file explicitly (`git diff --name-only HEAD -- dragonballs`
plus untracked files) instead of the directory made the same commit pass clean.

Second, smaller issue from the same session: an earlier attempt piped the script into `| tail -8`
(a rule violation SKILL.md already names), which cut off the REFUSED line so it looked like a clean
exit-0 run with no commit. The rule exists; noting it only because the truncated output hid the
directory bug above for one round.

## Approach
In `commit-pathspec.sh`, before own-range derivation and foreign-hunk-check, expand any pathspec
entry that is a directory into its changed files (`git diff --name-only HEAD -- <dir>` plus
`git ls-files --others --exclude-standard -- <dir>`), and run both checks per expanded file. Keep
the commit itself on the original pathspec (or the expanded list; either commits the same set).
Alternatively refuse a directory pathspec outright with a message telling the caller to expand it.

## Acceptance
- A commit whose pathspec includes a directory with several changed files, all own, passes
  foreign-hunk-check without `--force` and without per-file `--own-range` flags when only one
  session marker is live.
- A self-test in the commit skill's test suite (or `ci/run_all.py`) covers a directory pathspec
  with two changed files whose hunk line numbers overlap.

## Notes

- Done 2026-10-08: a directory pathspec entry is expanded into its changed tracked and untracked files before own-range derivation and foreign-hunk-check. Root cause: the concatenated directory diff fed foreign-hunk-check a +++ b/<next file> header that read as added content at the previous file's line numbers. Test r52 reproduces the two-file refusal and passes clean.
