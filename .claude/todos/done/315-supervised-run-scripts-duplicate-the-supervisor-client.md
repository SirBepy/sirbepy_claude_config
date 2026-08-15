<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=5, reconfirm-count=1, content-hash=9b2e096b -->
# restart-and-wait.ps1 copies sv.ps1's supervisor client instead of sharing it

**Type:** task
**Origin:** ai

## Goal

Extract the supervisor connection helpers that `sv.ps1` and `restart-and-wait.ps1` both carry into
one dot-sourceable file, so the token/port resolution lives in exactly one place.

## Context

Found by the `/code-check` pass of the 2026-08-13 `/auto-do-todos` session, which had just created
`restart-and-wait.ps1` (todo 306) in the same run that extracted two OTHER shared modules
(`skills/_shared/playwright-resolve.cjs` and `skills/_shared/figma_client.py`) specifically to kill
this same duplication pattern. This one was missed.

- `skills/supervised-run/restart-and-wait.ps1:43-59` carries `$dataDir`, `Get-SupervisorConfig` and
  `Invoke-Api`.
- `skills/supervised-run/sv.ps1:64` and `:68-76` and `:97-105` carry the originals.

`Get-SupervisorConfig` is copied verbatim. `Invoke-Api` is a near-identical subset that drops the
`$Body` parameter.

The likely reason it was copied rather than reused: `sv.ps1` is a `param()`-driven script, so
dot-sourcing it would execute it rather than just load its functions. That is a real obstacle, but it
argues for extracting the shared part, not for keeping two copies. The cost of two copies is
concrete: the supervisor's token file location or port-discovery scheme changing means finding both.

## Approach

Move `$dataDir`, `Get-SupervisorConfig` and `Invoke-Api` into `skills/supervised-run/_common.ps1`,
then dot-source it from both scripts. Keep `Invoke-Api`'s `$Body` parameter, since the shared version
has to serve `sv.ps1`'s POST calls too, and `restart-and-wait.ps1` simply will not pass it.

Underscore prefix matches the convention already used by `hooks/_hooklib.py` and `skills/_shared/`.

## Acceptance

- `Get-SupervisorConfig` and `Invoke-Api` are each defined exactly once across `skills/`.
- `sv.ps1 ls` still works against the live supervisor.
- `restart-and-wait.ps1` still reports correctly for a nonexistent id and for a `-NoRestart` wait
  whose marker never appears, the two cases its original verification actually exercised.

## Notes

- Filed by `/close` Phase 2 on 2026-08-13.
- Do NOT restart or reload one of Joe's live supervised entries to test this. The original build of
  `restart-and-wait.ps1` deliberately left the `/reload` and `/restart` POST paths unexercised for
  that reason, and that constraint still holds.
- Completed via /auto-do-todos 2026-08-15: extracted $dataDir, Get-SupervisorConfig and Invoke-Api into skills/supervised-run/_common.ps1, dot-sourced from both sv.ps1 and restart-and-wait.ps1 via $PSScriptRoot so resolution is independent of the caller cwd (verified by running both from C:\tmp with absolute paths). The two original Invoke-Api copies differed only in signature: sv.ps1 had a 4th optional $Body that branched to a JSON POST, restart-and-wait.ps1 had 3 params; the superset was adopted, which is behaviour-preserving since restart-and-wait never passed a body. SKILL.md needed no change, it has no enumerated file-layout section.
