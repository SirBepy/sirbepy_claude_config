<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1352 is the same tool but a different failure (a setup error read as RED); this one deletes files outside the temp worktree -->
# red-check's teardown follows a junction into the main checkout and deletes files there

**Type:** task
**Origin:** ai
**Summary:** `tools/red-check.ps1` removes its temp worktree with `git worktree remove --force`, which followed a node_modules junction the test command made and deleted the main checkout's `node_modules/.bin`.

## Why

A tool whose job is to never touch the live tree deleted shared files another session's dev server and every frontend2 worktree junction depend on.

## Context

2026-11-13, fibo, /auto-do-todos sub session 6a17bde3. A Node repo's pre-fix worktree has no `node_modules`, so the only way to run vitest there is a junction to the main checkout's (the same junction the fibo worktrees use). The TestCommand made `frontend2\node_modules` a junction; red-check's `finally` then ran `git worktree remove $tmp --force` (`tools/red-check.ps1` around line 113). git recursed through the junction, deleted `C:\Users\tecno\Desktop\Projects\fibo\frontend2\node_modules\.bin` whole, stopped on a locked file, and had already deregistered the worktree. Repaired with `npm rebuild --ignore-scripts` in the main checkout (135 bin links back). `tools/safe-remove-worktree.ps1` exists for exactly this hazard and red-check does not use it.

A second, smaller trap from the same run: a TestCommand joined with `&` (cmd style) is PowerShell's background-job operator under `Invoke-Expression`, so the test ran nowhere, exited non-zero and red-check printed "RED confirmed". pc-1352's INCONCLUSIVE rule would also catch that case.

Working shape that followed: TestCommand `cmd /c mklink /J frontend2\node_modules <main>\frontend2\node_modules | Out-Null; Push-Location frontend2; npx vitest run <files>; $c=$LASTEXITCODE; Pop-Location; cmd /c rmdir frontend2\node_modules; cmd /c exit $c`. It unlinks the junction itself before teardown.

## Approach

1. Tear down through `safe-remove-worktree.ps1` (it unlinks every reparse point non-recursively first), never a bare `git worktree remove --force`.
2. Offer a `-LinkNodeModules <dir>` (or a generic `-Junction <rel>=<target>`) parameter that red-check makes and unlinks itself, so callers stop hand-rolling the junction.
3. Document the `;` vs `&` point in the script's .EXAMPLE.

## Acceptance

- A red-check run whose TestCommand leaves a junction inside the temp worktree leaves the junction's target untouched (test: junction to a scratch dir holding a marker file; the marker survives).
- A Node repo can be red-checked with one parameter for node_modules, no hand-written junction.
