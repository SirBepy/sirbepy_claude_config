<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# build-watch.md should explicitly warn against wrapping the watcher launch in Start-Process

**Type:** skill-improvement
**Origin:** ai

## Goal

Prevent a repeat of a self-inflicted watcher failure: launching `watch-build.ps1` via
`Start-Process` (or any detached-process wrapper) instead of invoking it directly with
`run_in_background: true`, which both defeats the harness's own completion tracking AND risks a
duplicate-process PID-file collision if the direct form also gets launched.

## Context

`~/.claude/skills/commit/build-watch.md` step 3 gives the exact command to run
(`& "...\watch-build.ps1" -Branch <branch> -RepoPath <path>`) and says to run it "in the
background" - it doesn't explicitly say *how* to background it. In `windows_taskbar_widgets`
(2026-08-09), Claude wrapped that command in `Start-Process ... -WindowStyle Hidden` inside a
`PowerShell` tool call with `run_in_background: true`. This created two problems:
1. The `Start-Process` call itself is non-blocking, so the wrapping tool call returned almost
   instantly (harness saw a fast "completed" task) - the harness never actually tracked the real
   watcher process, so the documented "you'll be re-invoked when the watcher exits" behavior
   couldn't fire for it.
2. Claude then correctly re-launched the watcher a second time via the DIRECT documented form
   (`run_in_background: true` on the script call itself, no `Start-Process`) to get real harness
   tracking - leaving two `watch-build.ps1` instances running concurrently, both trying to write
   the same `skills\commit\watch-build.pid` file. Claude caught this and killed the stray
   `Start-Process`-launched instance, but the surviving (correct) watcher then failed with exit
   code 4 and zero output - plausibly a side effect of the PID-file contention, though this wasn't
   confirmed with certainty (the actual CI result was independently verified green via
   `gh run list` instead).

## Approach

Add an explicit line to `build-watch.md` step 3, right next to the launch command: something like
"Invoke this directly via the tool's own `run_in_background: true` - never wrap it in
`Start-Process`/`nohup`/similar detached-process helpers, which hides it from the harness's
completion tracking and can race the PID file if invoked twice." This mirrors how the skill already
calls out other easy-to-get-wrong mechanics (literal path vs `$env:`-built, the `-TimeoutMinutes`
override).

## Acceptance

- A future session reading build-watch.md's step 3 has no ambiguity about backgrounding mechanism.
- Bonus (optional, not required): `watch-build.ps1` itself could detect an existing live PID in its
  `.pid` file at startup and refuse to run a second instance rather than silently racing - out of
  scope for this todo's minimal fix, but worth a `## Notes` mention if whoever picks this up wants
  to go further.

## Notes

Filed globally (not in `windows_taskbar_widgets`'s own backlog) per CLAUDE.md's rule that findings
about the global `~/.claude` tree belong in `~/.claude/todos/` regardless of which project session
surfaced them.
- Duplicate of 75 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
