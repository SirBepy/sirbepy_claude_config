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
