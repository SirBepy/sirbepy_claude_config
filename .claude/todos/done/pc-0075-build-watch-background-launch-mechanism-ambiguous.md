<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=7, reconfirm-count=2, content-hash=fe424ebd -->
# build-watch.md's "launch in the background" step doesn't say HOW, and the wrong choice breaks re-invocation

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `~/.claude/skills/commit/build-watch.md` step 3 explicit about the launch mechanism, so an
agent doesn't default to a detached process that the harness can never re-invoke with results.

## Context

`build-watch.md` step 3 says: "Launch the watcher in the background" and gives the raw
`watch-build.ps1` invocation, with step 4 promising "you'll be re-invoked when the watcher
exits." In a 2026-08-10 `windows_taskbar_widgets` session, this was read as "detach it" and
launched via `Start-Process -WindowStyle Hidden` (PowerShell native backgrounding). That works as
a process launch, but it runs OUTSIDE the harness's own background-task tracking, so step 4's
"you'll be re-invoked" never happens - the process just runs to completion with nobody watching.
Caught only because the stray process was later found via `Get-CimInstance` and killed, then
relaunched correctly using the PowerShell tool's own `run_in_background: true` parameter, which
DOES produce a task notification on completion.

## Approach

Add one explicit line to `build-watch.md` step 3: launch via the tool's own `run_in_background:
true` parameter (PowerShell/Bash tool), not `Start-Process`/`nohup`/`&`-style shell detaching -
only the harness's own background-task mechanism triggers the "re-invoked with its stdout"
promise in step 4. Consider naming the exact tool-call shape (e.g. a one-line example) so this
isn't left to inference next time.

## Acceptance

- `build-watch.md` step 3 names the harness `run_in_background` mechanism explicitly, not just
  "launch in the background."
- A future agent following the doc launches it correctly on the first try.

## Notes

- completed, commit 267d5f9

## Merged in (2026-08-11)

Absorbed todos 66, 69, 224 during /cleanup-todos. Their full text is in `done/` - read them before implementing, they carry specifics this file does not.
