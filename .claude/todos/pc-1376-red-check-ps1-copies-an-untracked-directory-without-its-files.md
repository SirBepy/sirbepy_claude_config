<!-- Claim before executing: .claude/todos/.claims/ per refs/ai-todos-format.md -->
<!-- duplicate-checked: grepped todos for red-check; pc-1337..1342 mention it only in passing, none covers untracked dirs -->
# red-check.ps1 overlay copies an untracked directory as an empty folder

**Type:** task
**Origin:** ai
**Summary:** `tools/red-check.ps1` reads `git status --porcelain`, which lists a wholly untracked directory as one `?? dir/` line, then runs `Copy-Item -LiteralPath <dir> -Destination <dest> -Force` without `-Recurse`, so the pre-fix worktree gets an empty folder and the test run reports "Does not exist" as a false "RED confirmed".

## Why

Seen 2026-11-18 in zng-app (sc-54974): new test files under untracked directories `test/ui/ds/buttons/` etc. never reached the pre-fix worktree. The script printed `Failed to load ... Does not exist` and then "RED confirmed: test failed against pre-fix code (exit 1)", which proves nothing about the fix. The real red had to be reproduced by hand in a scratch worktree.

## Context

- File: `C:\Users\tecno\.claude\tools\red-check.ps1`, the overlay `foreach ($p in $dirty)` loop (`Copy-Item` at the overlay step).
- Fix idea: pass `-Recurse` when `$src` is a directory, or list untracked files with `git status --porcelain --untracked-files=all`. Also make the script refuse to print "RED confirmed" when the output contains "Does not exist" / "Failed to load" for a test path it was given.
- Test: a repo with one untracked new test directory and one tracked fix path, assert the test file exists in the scratch worktree before the command runs.
