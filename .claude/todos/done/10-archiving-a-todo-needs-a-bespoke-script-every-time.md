<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=1, content-hash=d450a52d -->
# Archiving a todo needs a hand-written throwaway script every single time

**Type:** skill-improvement

## Goal

Let a session append a completion note and archive a todo in one call, instead of authoring a
disposable PowerShell script per batch.

## Context

`~/.claude/skills/close/complete-todo.ps1` already handles the mechanical half well: move to `done/`,
prune the PLAN.md line, release the claim. What it does NOT do is append the Notes line that
`ai-todos-format.md` requires before archiving.

So every completion becomes: hand-write a script that reads the file, finds or creates `## Notes`,
appends a line with the right encoding, then calls `complete-todo.ps1`. On 2026-08-07 a single
`/auto-do-todos` run in `windows_taskbar_widgets` wrote NINE such scripts to `C:\tmp`
(`close-skips.ps1`, `close-batch-a/b/c.ps1`, `close-2335.ps1`, `close-17-39.ps1`, `close-41-43.ps1`,
`close-26.ps1`, `close-19.ps1`, `close-42.ps1`), each one a near-copy of the last.

Two recurring details each rewrite has to get right independently, and either one silently corrupts
the file if missed:

- UTF8 **without** BOM, via `[System.IO.File]::WriteAllText`. `Set-Content -Encoding utf8` on Windows
  PowerShell 5.1 prepends a BOM, which is now banned outright by global CLAUDE.md's Shell Commands
  section.
- Insert under an existing `## Notes` heading if there is one, create the heading if not, and place
  it after `## Acceptance` rather than at the end when an `## Open questions` block is present.

## Approach

Add a `-Note <string>` parameter to `complete-todo.ps1` that does the append before the move, using
`[System.IO.File]::WriteAllText` with a BOM-less UTF8 encoding. Match the existing `## Notes`
heading when present, create it when absent, and preserve any `## Open questions` block's position.

Then update `ai-todos-format.md` and any skill that archives todos (`/close`, `/batch-todos`,
`/cleanup-todos`, `/auto-do-todos`) to call it with `-Note` instead of describing a hand-rolled
append.

Consider also accepting several ids in one invocation, since batches of 2-4 completions were the
common shape in that run.

## Acceptance

- Completing a todo with a note is one call: `complete-todo.ps1 -Id <id> -Note "<text>"`.
- The written file has no BOM (first bytes are not `239,187,191`).
- An existing `## Notes` section is appended to, not duplicated.
- A todo carrying `## Open questions` keeps that block in place.
- No skill still instructs a session to hand-write the append.

## Notes

Found by `/close` on 2026-08-07. Filed here rather than in the project backlog per the rule added to
global CLAUDE.md the same day: todos about the global `~/.claude` tree belong in this backlog.
- Implemented 2026-08-08: `complete-todo.ps1` gained `-Note`, matching an existing `## Notes` heading or creating one after `## Acceptance`, BOM-less via `WriteAllText`. Also fixed the pre-existing BOM bug in its PLAN.md prune write and in `claim-todo.ps1`'s temp-file write (same defect class, same file/adjacent file). Updated `ai-todos-format.md` and `batch-todos/SKILL.md` step 6.4 to call `-Note`; did not sweep `auto-do-todos`/`cleanup-todos`/`pickup` (out of this dispatch's scope, still describe manual append - worth a follow-up).
