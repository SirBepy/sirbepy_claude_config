<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=1, content-hash=feb5d90c -->
# Clarify build-watch.md's launch mechanism so it can't be misread as a raw shell command

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/commit/build-watch.md`'s step 3 gave the watcher launch as a bare `& "...\watch-build.ps1"
...` invocation with no note that it must go through the harness's own background-execution
mechanism (the tool call's `run_in_background: true` parameter), not a raw detached process spawn.

## Context

2026-08-11, `claude_usage_in_taskbar` session: read step 3 literally and launched the watcher via
`Start-Process -FilePath powershell.exe -ArgumentList ... -WindowStyle Hidden` - a real detached
OS process with no harness tracking, so there was no way to be notified when it exited (the whole
point of "you'll be re-invoked when the watcher exits" a few lines later in the same doc).  Caught
it, killed the stray process (`Stop-Process`), and relaunched correctly by calling the same command
through the PowerShell tool's `run_in_background: true` param instead - which the doc never states
is the required mechanism.

## Approach

Add a one-line note to `skills/commit/build-watch.md` step 3, right above or inside the code
example: launch via the tool call's own `run_in_background: true` parameter (Bash or PowerShell
tool), never `Start-Process`/`nohup`/a manually detached process - only the harness-tracked form
lets the "you'll be re-invoked when the watcher exits" behavior in step 4 actually work.

## Acceptance

- `build-watch.md` step 3 explicitly names the launch mechanism, not just the command line.
- A future session reading it launches via `run_in_background: true` on the first attempt.

## Notes

- Duplicate of 75, which already absorbed three earlier copies of this build-watch launch-mechanism finding. Merged during /cleanup-todos 2026-08-12. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
