---
name: sentry
description: Triage open Sentry issues across zng-app, zng-admin, zng-biller. Buckets by ACT/WATCH/REVIEW/CLOSE with delta tracking from a local snapshot.
argument-hint: "[--issue <id>]"
---

# /sentry

Triage open Sentry issues across all 3 ZNG projects.

## Trigger

- `/sentry` — full triage run (described below)
- `/sentry --issue <id>` — drill into one issue

## Drill-in

Run:
```powershell
& "C:\Users\tecno\.claude\scripts\Get-SentryIssue.ps1" <id> -Org zirtue-nk
```

## Full triage run

Run this using the PowerShell tool:

```powershell
& "C:\Users\tecno\.claude\scripts\Invoke-SentryTriage.ps1"
```

**Config (hardcoded in the script):**
- Snapshot: `$env:USERPROFILE\.claude\.sentry_snapshot.json`
- Token: `$env:SENTRY_AUTH_TOKEN` (User scope)
- Org: `zirtue-nk`
- Projects: `zng-app`, `zng-admin`, `zng-biller`

## After the script runs

One-line summary: `ACT: X | WATCH: X | REVIEW: X | CLOSE: X`.

Then analyze the results and present options via AskUserQuestion:
- Bundle issues that are related (same screen, same error class, same feature area) into a single option.
- Each option = one thing to work on (a single issue or a logical bundle of 2-3).
- Add a "Nothing for now" option.
- Max 4 options total.
- Label each option with the issue title(s) and event count so the dev can skim without re-reading the table.

Example option labels:
- "Fix null-check crash on loan-application (21 events)"
- "Investigate LateInitializationError + GoRouter crash (14 + 5 events, both app-init)"
- "Close WKWebView noise (1 event, benign iOS)"
- "Nothing for now"
