<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=7, reconfirm-count=2, content-hash=3b262cf3 -->
# sentry: add an absolute ACT-bucket severity floor and follow the pagination cursor past limit=100

**Type:** skill-improvement

## Goal

`skills/sentry/SKILL.md` drives `C:\Users\tecno\.claude\scripts\Invoke-SentryTriage.ps1`,
which buckets issues into ACT/WATCH/REVIEW/CLOSE using PURELY RELATIVE thresholds
(quartiles within the current unresolved-issue set) and fetches only the first page of
results (`limit=100`, no cursor follow-up). Both are gaps: (1) a quiet day with few
issues can push a genuinely low-severity issue into ACT purely because it's relatively
higher than its neighbors, and a bad day with 100+ issues can silently drop real issues
past the first page; (2) add an absolute severity floor to the ACT bucket, and (3) follow
Sentry's pagination past `limit=100`.

## Context

`C:\Users\tecno\.claude\scripts\Invoke-SentryTriage.ps1` (as of 2026-08-01):

- Line 60: single-page fetch, no cursor/link-header follow-up:
  ```powershell
  $page = Invoke-RestMethod -Uri "$base/projects/$org/$slug/issues/?query=is:unresolved&sort=date&limit=100" -Headers $headers
  ```
  Sentry's issues API paginates via a `Link` response header (`rel="next"`, cursor-based).
  This script reads `$page` once and never inspects that header, so any project with more
  than 100 unresolved issues silently loses everything past the first 100.

- Lines 104-113: ACT/WATCH bucketing is purely relative (quartile-based), no absolute
  floor:
  ```powershell
  $sorted = @($grp.Group | Sort-Object events)
  $median = $sorted[[int]($sorted.Count / 2)].events
  $q3     = $sorted[[int]($sorted.Count * 0.75)].events
  ...
  if ($iss.events -ge $q3)         { $actList.Add($iss) }
  elseif ($iss.events -ge $median) { $watchList.Add($iss) }
  ```
  There is also a floor-style CLOSE filter at line 95 (`$iss.events -lt 10 -and
  $iss.lastSeen -lt $threshold30d -and $iss.users -lt 3`) but nothing analogous gating
  ACT from below - an issue can land in ACT with a single-digit event count on a quiet
  day just by being in the top quartile of a small batch. Each issue object already
  carries `events` (line 73) and `users` (line 75) and an `isRegr`-style regression flag
  is available from the Sentry API's issue payload (confirm the exact field name against
  the live API response shape when implementing - it may need adding to the object
  built around line 73).

## Approach

1. Read `C:\Users\tecno\.claude\scripts\Invoke-SentryTriage.ps1` in full before editing.
2. **Pagination:** after the `Invoke-RestMethod` call at line 60, inspect the response
   headers for a `Link` header with `rel="next"` (Sentry's documented pagination
   mechanism for this endpoint) and loop, appending pages, until no `next` link remains
   or a safety cap (e.g. 10 pages / 1000 issues) is hit. `Invoke-RestMethod` in Windows
   PowerShell 5.1 does not expose response headers directly on `-Headers`-based calls in
   older syntax - use `Invoke-WebRequest` instead (matching the pattern already used
   elsewhere in this codebase for header access, e.g. `skills/linear/SKILL.md`'s
   `Invoke-Linear` helper) or the `-ResponseHeadersVariable` parameter if the PowerShell
   version supports it, and parse `.Content | ConvertFrom-Json`.
3. **Absolute ACT floor:** add a floor condition alongside the existing quartile check at
   line 112 - e.g. `$iss.events -ge $q3 -or $iss.events -ge <N> -or $iss.users -ge <M>
   -or $iss.isRegr`. Pick concrete values for `<N>` (event count) and `<M>` (user count)
   by sampling recent real triage runs' snapshot data (`$env:USERPROFILE\.claude\.sentry_snapshot.json`,
   referenced at SKILL.md line 32) if available, otherwise default conservatively (e.g.
   `N=25`, `M=5`) and note the choice is a starting guess in the commit message.
4. Confirm the regression-flag field name against a live `is:unresolved` issue payload
   before wiring `isRegr` in - Sentry's API field for "is this a regression" may be named
   differently (e.g. under `substatus` or a boolean on the issue object); do not assume
   the name without checking the actual JSON shape.

## Acceptance

- A project with >100 unresolved issues has all of them considered for bucketing, not
  just the first page - verify by triggering `/sentry` against a project known to exceed
  100 unresolved issues (or temporarily lowering `limit=` to force multi-page behavior
  during testing, then reverting).
- An issue with high absolute event/user count, or flagged as a regression, lands in ACT
  even when the rest of the batch is quiet (i.e. even below the relative q3 threshold).
- Existing WATCH/REVIEW/CLOSE logic (lines 95, 113 and surrounding) is otherwise
  unchanged - this todo only adds an OR-condition to ACT's gate and extends the fetch
  loop, it does not redesign the bucketing algorithm.
