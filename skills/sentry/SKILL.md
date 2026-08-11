---
name: sentry
description: Triage open Sentry issues across zng-app, zng-admin, zng-biller. Buckets by ACT/WATCH/REVIEW/CLOSE with delta tracking from a local snapshot.
argument-hint: "[--issue <id>]"
---

# /sentry

Triage open Sentry issues across all 3 ZNG projects.

## Trigger

- `/sentry` - full triage run (described below)
- `/sentry --issue <id>` - drill into one issue

## Drill-in

`Get-SentryIssue.ps1` takes a short ID directly (e.g. `ZNG-APP-96`), a numeric issue ID, or a full issue URL. It resolves short IDs itself via the shortIDLookup API:

```powershell
& "C:\Users\tecno\.claude\scripts\Get-SentryIssue.ps1" ZNG-APP-96 -Org zirtue-nk
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

## Per-issue write-up (when analyzing/drilling into specific issues)

For each issue, check the noise gate first: if it's third-party/extension noise, stop there; the rest of the fields don't apply. Two independent noise signals, either is sufficient:
- Stack trace is entirely non-app frames, e.g. `chrome-extension://...`, MetaMask, `runtime.sendMessage`, `Object Not Found Matching Id`.
- **Sparse-tag signature** (confirmed 2026-08-06): event has only `dist/environment/handled/interface_type/level/mechanism/release` tags, no `browser`, `url`, `user`, `breadcrumbs`, or `request` entry, AND the single stack frame has `filename: "undefined"` (literal string) with `function: null`. Real app errors (Dart/JS) always carry a resolved filename and rich context even when the message itself is generic. This signature held even when source maps were confirmed uploaded for that release: the browser itself never reported a filename, which happens for cross-origin/extension-injected scripts caught by the page's global `onerror`/`onunhandledrejection` handlers, not failed source-map resolution.

Each field is its own bullet on its own line, never collapse fields into one paragraph or one run-on line (plain `\n` alone renders as a single line in markdown; use a bullet list, which forces real line breaks). Separate each issue with a `---` divider and a `###` heading.

```
### Sentry Issue Name (ID)

- **Noise (third-party/extension, not app code):** true/false, if true stop here
- **Events / Users / Pattern:** e.g. 20 events, 0 users, Ongoing 4wk
- **Breaking bug:** true/false
- **Should it be rushed:** true/false
- **Where:** screen/flow
- **Why:** recent FE change / BE change / new feature / Flutter issue / unknown (confidence: confirmed from code / inferred from stack trace / speculative)
- **Can it be fixed on FE:** true/false
- **Disposition:** Fixed / Won't-fix (external, e.g. Plaid) / Blocked-upstream (e.g. tracked Flutter issue) / Needs fix / Ignored-noise
- **Fix / next step:** ...

---
```

Carry disposition across `/sentry` runs when re-triaging the same issue, don't re-diagnose an issue already marked Fixed/Won't-fix/Blocked-upstream unless its event count jumped since the last snapshot.
