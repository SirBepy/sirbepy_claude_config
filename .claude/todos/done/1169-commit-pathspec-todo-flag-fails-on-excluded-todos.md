<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits are about client-repo slug matching, overlap refusal and AI-attribution trailers; none covers --todo staging an ignored todo path -->
# commit-pathspec.sh --todo aborts the commit when the repo excludes .claude/todos/

**Type:** skill-improvement
**Origin:** ai

## Goal

`commit-pathspec.sh --todo <id>` works (or cleanly no-ops) in a repo whose `.claude/todos/` is git-ignored, instead of failing the whole commit.

## Context

2026-10-12, mc_plugins_tag (`C:\Users\tecno\Desktop\Projects\mc_plugins_tag`): after `complete-todo.ps1 -Id 142`, `commit-pathspec.sh ... --todo 142 -- <3 files>` ran every check clean, then printed `[commit] ERROR: could not stage untracked file .claude/todos/done/142-guildmaster-bounty-exclusion-complaint.md` and committed nothing. Cause: that repo's `.git/info/exclude:8` has `.claude/todos/` (the ai-todos git policy for a repo that keeps todos local), so `git add` refuses the ignored path. Rerunning without `--todo` committed fine.

## Approach

In `skills/commit/commit-pathspec.sh`'s `--todo` expansion, drop any resolved todo path that `git check-ignore -q` reports as ignored (print one info line naming it), so the flag is safe to pass in every repo regardless of its todo git policy. Add a case to the script's test suite with an excluded `.claude/todos/`.

## Acceptance

- `--todo <id>` in a repo with `.claude/todos/` excluded commits the named files and prints that the todo path was skipped as ignored.
- The script's tests pass.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): --todo drops a todo path git check-ignore reports and prints a skip line; test RED then GREEN.
