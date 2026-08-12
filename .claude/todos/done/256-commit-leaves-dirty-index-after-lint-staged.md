<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=2, content-hash=fe2defde -->
# /commit leaves a dirty index behind after a pathspec commit in a lint-staged repo

**Type:** skill-improvement
**Origin:** ai

## Goal

Add a post-commit index-refresh step to `/commit` so a pathspec commit in a repo with a
`lint-staged` pre-commit hook does not leave the working tree looking dirty when it is not.

## Context

Observed across 19 commits in one session on 2026-08-11 in the fibo repo.

`/commit` step 8's `git commit -m "..." -- <paths>` form is correct and safe, and should not change.
But when the repo's `pre-commit` hook runs `lint-staged`, the hook rewrites those files (prettier
plus `eslint --fix`) and applies the result into the commit. Afterwards:

- `git status` reports the committed files as modified, while `git diff HEAD` is **empty**. The
  working-tree files carry LF, the index entry expects CRLF under `core.autocrlf`, so the entries
  are left stat-dirty.
- In one case the shared index also kept a stale version of a file (7 lines deleted) that had
  already been committed correctly, showing as `MM` in `git status`.

Left alone this reads as uncommitted work at the end of a session, and can contaminate the next
commit's file list.

The fix that worked, verified the same day: after the commit, `git add` the just-committed paths.
That refreshes their index entries so the index matches the working tree, which already matches
HEAD, leaving nothing to commit.

Two things that do NOT work or are unsafe here:

- `git update-index --refresh` is insufficient. It reports "needs update" for each file and stops.
- `git reset` must never be used for this. The repo may be shared with concurrent sessions and a
  reset disrupts their commit prep. `git add` is purely additive and safe.

## Approach

File: `C:\Users\tecno\.claude\skills\commit\SKILL.md`.

Add a short step 8b, conditional on a `lint-staged` pre-commit hook being present (detect via
`git config core.hooksPath` and reading the resulting `pre-commit`): re-`git add` the exact paths
just committed, and print them, so the refresh is visible rather than silent. Note in the step why
`git reset` is forbidden and why `update-index --refresh` is not enough, so a future reader does not
"simplify" it back into either.

## Acceptance

- After `/commit` in a lint-staged repo, `git status` is clean when nothing else is outstanding.
- The step prints which paths it refreshed.
- No `git reset` anywhere in the added step.

## Notes

- completed, commit 0796403
