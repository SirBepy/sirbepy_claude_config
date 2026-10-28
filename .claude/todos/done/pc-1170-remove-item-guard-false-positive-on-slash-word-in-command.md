<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits are WriteAllText cwd resolution, em-dash scanning, skill-eval headings and shell-write angle brackets; none is the removal guard misreading a string literal as a target -->
# Remove-Item guard treats a "/word" inside unrelated string text as a protected system path

**Type:** skill-improvement
**Origin:** ai

## Goal

The PowerShell removal guard only judges the actual Remove-Item target paths, not every `/something` token elsewhere in the same command.

## Context

2026-10-12, mc_plugins_tag session: one PowerShell call did `[IO.File]::WriteAllText(...)` on a todo file whose new text contained "Written by /auto-do-todos on 2026-10-12", then `Remove-Item .claude/todos/.claims/136.claim`. The whole call was refused with `Remove-Item on system path '/auto-do-todos' is blocked. This path is protected from removal.` - the guard took the slash-word from the string literal as a removal target. Nothing in the call ran (the file write was lost too). Rerunning `Remove-Item -LiteralPath "<absolute claim path>"` alone worked. UNVERIFIED which hook emits that message; grep `hooks/` for "is blocked. This path is protected".

## Approach

Find the guard (likely a PreToolUse hook parsing PowerShell commands, possibly sharing code with the drive-root-child protection). Make it extract only Remove-Item's `-Path`/`-LiteralPath`/positional arguments for its system-path check, not every slash-prefixed token in the command. Add a test with a Remove-Item of a repo file next to a string literal containing `/auto-do-todos`.

## Acceptance

- The command shape above is allowed; `Remove-Item /` and real system paths are still blocked.
- The hook's self-test suite passes.

## Notes

- 2026-10-13, claude_usage_in_taskbar /auto-do-todos: second hit. `complete-todo.ps1 -Note "Archived via /cleanup-todos ..."; Remove-Item -Recurse -Force c:\tmp\cleanup-2026-10-13\todos` refused as `system path '/cleanup-todos'`; the marker update and todo archive chained before it silently did not run either, noticed only by re-checking state.
- 2026-10-20, claude_usage_in_taskbar /auto-do-todos (session cec6b3d2): third and fourth hits. Twice, a `complete-todo.ps1 -Note "... /auto-do-todos, ..."` call shared one PowerShell command with an unrelated `Remove-Item <exact claim or scratch file>`. Both were refused as `system path '/auto-do-todos,'` (trailing comma included), and every archive in that command was skipped. Workaround used: put the Remove-Item in its own tool call.
- Dropped by the cleanup-todos pass 2026-10-23: the Remove-Item system-path denial is emitted by claude.exe itself, no hook in this repo emits it, so the stated fix is impossible here (it fired again on this very archive call). The keep-Remove-Item-in-its-own-call workaround was folded into 1167.
