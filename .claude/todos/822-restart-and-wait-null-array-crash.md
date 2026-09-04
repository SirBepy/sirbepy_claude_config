<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=5, reconfirm-count=3, content-hash=7314d696 -->
<!-- duplicate-checked -->
# supervised-run restart-and-wait.ps1 crashes with "Cannot index into a null array"

**Type:** task
**Origin:** ai

## Goal

`restart-and-wait.ps1 -Id <id>` works for a healthy flutter entry instead of dying before doing anything.

## Context

2026-08-27, zng-app session: `powershell -File "C:\Users\tecno\.claude-personal\skills\supervised-run\restart-and-wait.ps1" -Id "zng-app:flutter-run-8"` exited 1 with `Cannot index into a null array` (no line number surfaced). The entry was healthy and running; the raw API fallback worked immediately (`Invoke-Api $cfg 'POST' '/procs/zng-app:flutter-run-8/reload' $null` via `_common.ps1`). So the bug is in the script's own lookup/marker logic, not the supervisor.

## Approach

Reproduce with a running flutter entry, find the null-indexed collection (likely the procs lookup or the readiness-marker table for the `flutter` kind), fix, and have it print a real error naming what was null instead of the bare exception.

## Acceptance

- `restart-and-wait.ps1 -Id <healthy flutter entry>` restarts/reloads and waits for the marker.
- A genuinely missing id produces a clear one-line error, not a null-array crash.

## Notes

- INVESTIGATED in the /mega-todos wave-2 run on 2026-09-04. NO COMMIT was made, because no code
  change turned out to be needed for what could be verified.
- The original crash appears already fixed, incidentally, by `9fcd807` ("anchor restart-and-wait's
  freshness on log text, not on line count"). Two independent re-checks confirmed every API result
  that gets indexed is now `@()`-wrapped and `.Count`-guarded first: lines 60-61 (proc lookup),
  72-73 (log high-water mark), 83 and 88-93 (fresh-log windowing), and 112 (final log dump).
- Acceptance item 1 is UNVERIFIABLE without a live flutter process running under the supervisor.
  The supervisor itself was confirmed running and reachable, but there was no flutter entry to
  restart. This was NOT faked or worked around, and the item is not being claimed.
- Acceptance item 2 was the testable half and is the reason this todo stays open rather than being
  archived. Whoever picks it up should run the script against an id that does not exist and check
  the message names what was missing, per this todo's own Approach ("a real error naming what was
  null instead of the bare exception"). An unreachable supervisor deserves the same treatment.
- Do not archive this on the strength of the code reading above. The `@()` wrapping makes a crash
  unlikely; it does not prove the error message is useful, which is what item 2 actually asks.
