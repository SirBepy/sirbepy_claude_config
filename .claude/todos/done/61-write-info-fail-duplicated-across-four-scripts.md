<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Write-Info / Write-Fail are copy-pasted into four PowerShell helpers

**Type:** task
**Origin:** ai

## Goal

Decide whether the duplicated `Write-Info` / `Write-Fail` pair gets extracted into one shared file
or is deliberately left duplicated, and record the decision so the next helper script does not
re-litigate it.

## Context

Found by `/code-check` during `/close` on 2026-08-08, scoped to that session's diff.

The same two one-line functions are defined identically in four scripts:

- `skills/close/claim-todo.ps1:41-42`
- `skills/close/complete-todo.ps1:53-54`
- `skills/close/safe-remove-worktree.ps1:44-45` (new 2026-08-08)
- `skills/supervised-run/sv.ps1:61-62` (new 2026-08-08)

Both definitions are `function Write-Info($msg) { Write-Host $msg }` and
`function Write-Fail($msg) { Write-Error $msg }`, byte-identical in all four.

It was two copies before that session and is four after, so the pattern is actively spreading:
every new helper copies the preceding one. That trajectory, not the eight duplicated lines
themselves, is what makes this worth a decision.

## Approach

Three of the four live under `skills/close/`, so the cheap version is a `skills/close/_log.ps1`
dot-sourced by those three, with `sv.ps1` left alone rather than taking a cross-skill path
dependency for two lines.

Weigh honestly before doing it. Dot-sourcing introduces a path the caller must resolve relative to
its own location, and a broken relative path fails at runtime rather than at parse time, which is a
worse failure mode than eight duplicated trivial lines. "Leave it duplicated, write the decision
down" is a legitimate outcome here and should be recorded in the scripts or in
`close/ai-todos-format.md` rather than silently re-decided by whoever writes helper number five.

Do not extract across skill folders. `skills/close/` and `skills/supervised-run/` are independently
copyable units, and a shared `skills/_lib/` would couple them.

## Acceptance

- Either one shared definition exists and all sourcing scripts still parse and run (`claim-todo`,
  `complete-todo` and `safe-remove-worktree` each exercised at least once), or the duplication is
  documented as deliberate with the reason.
- No script gains a relative dot-source path that breaks when invoked from a different working
  directory. Verify by running each from a directory other than its own.

## Notes

Weak finding, filed for completeness rather than urgency. If the skill audit in todo 58 concludes
these helpers should merge or move anyway, close this as part of that work instead of doing it
twice.
- Dropped via /cleanup-todos 2026-08-11: the todo calls itself a weak finding, and its own analysis says the dot-source fix is worse than the duplication. Confirmed by dev 2026-08-11.
