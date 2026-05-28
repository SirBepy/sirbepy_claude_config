---
name: sentry
description: Triage open Sentry issues across zng-app, zng-admin, zng-biller. Buckets by ACT/WATCH/REVIEW/CLOSE with delta tracking from a local snapshot.
---

# /sentry

Triage open Sentry issues across all 3 ZNG projects.

## Trigger

- `/sentry` — full triage run (described below)
- `/sentry --issue <id>` — drill into one issue

## Drill-in

Run:
```powershell
& "$env:USERPROFILE\.claude\scripts\Get-SentryIssue.ps1" <id> -Org zirtue-nk
```

## Full triage run

Run the PowerShell script below **verbatim** using the PowerShell tool. Do not regenerate it.

**Config:**
- Snapshot: `$env:USERPROFILE\.claude\.sentry_snapshot.json`
- Token: `$env:SENTRY_AUTH_TOKEN` (User scope)
- Org: `zirtue-nk`
- Projects: `zng-app`, `zng-admin`, `zng-biller`

```powershell
$ErrorActionPreference = 'Stop'

$token = [Environment]::GetEnvironmentVariable('SENTRY_AUTH_TOKEN', 'User')
if (-not $token) { $token = $env:SENTRY_AUTH_TOKEN }
if (-not $token) { Write-Error 'SENTRY_AUTH_TOKEN not set'; exit 1 }

$headers = @{ Authorization = "Bearer $token" }
$base    = 'https://sentry.io/api/0'
$org     = 'zirtue-nk'
$targets = @('zng-app', 'zng-admin', 'zng-biller')

# --- Slug discovery ---
$allProjects = Invoke-RestMethod -Uri "$base/projects/" -Headers $headers
$matched = @($allProjects | Where-Object { $targets -contains $_.slug })
if ($matched.Count -eq 0) {
    $found = ($allProjects | ForEach-Object { $_.slug }) -join ', '
    Write-Error "No projects matched $($targets -join ', '). Found: $found"
    exit 1
}
$slugs = $matched | ForEach-Object { $_.slug }
Write-Host "Fetching: $($slugs -join ', ')"

# --- Load snapshot ---
$snapshotPath = "$env:USERPROFILE\.claude\.sentry_snapshot.json"
$snapshot     = @{}
$snapshotAge  = $null
if (Test-Path $snapshotPath) {
    $mtime       = (Get-Item $snapshotPath).LastWriteTime
    $snapshotAge = [int](((Get-Date) - $mtime).TotalHours)
    $raw         = Get-Content $snapshotPath -Raw | ConvertFrom-Json
    $raw.PSObject.Properties | ForEach-Object { $snapshot[$_.Name] = [int]$_.Value }
}
if ($snapshotAge -gt 36) {
    Write-Host "SNAPSHOT STALE (${snapshotAge}h) - delta values unreliable" -ForegroundColor Yellow
    Write-Host ''
}

# --- Fetch issues ---
$now    = Get-Date
$issues = [System.Collections.Generic.List[PSCustomObject]]::new()

foreach ($slug in $slugs) {
    try {
        $page = Invoke-RestMethod -Uri "$base/projects/$org/$slug/issues/?query=is:unresolved&sort=date&limit=100" -Headers $headers
    } catch {
        Write-Host "WARN: $slug - $($_.Exception.Message)" -ForegroundColor Yellow
        continue
    }
    foreach ($iss in $page) {
        $evts  = [int]$iss.count
        $delta = if ($snapshot.ContainsKey($iss.id)) { $evts - $snapshot[$iss.id] } else { $null }
        $fs    = [datetime]$iss.firstSeen
        $ls    = [datetime]$iss.lastSeen
        $issues.Add([PSCustomObject]@{
            id        = $iss.id
            title     = $iss.title
            events    = $evts
            delta     = $delta
            users     = [int]$iss.userCount
            firstSeen = $fs
            lastSeen  = $ls
            project   = $slug
            url       = $iss.permalink
            isNew     = ($fs -gt $now.AddHours(-24))
            isRegr    = ($fs -gt $now.AddDays(-7) -and $fs -le $now.AddHours(-24))
        })
    }
}

# --- Bucket ---
$threshold30d = $now.AddDays(-30)
$closeList    = [System.Collections.Generic.List[PSCustomObject]]::new()
$actList      = [System.Collections.Generic.List[PSCustomObject]]::new()
$watchList    = [System.Collections.Generic.List[PSCustomObject]]::new()
$reviewList   = [System.Collections.Generic.List[PSCustomObject]]::new()
$closeIds     = @{}

foreach ($iss in $issues) {
    if ($iss.events -lt 10 -and $iss.lastSeen -lt $threshold30d -and $iss.users -lt 3) {
        $closeList.Add($iss)
        $closeIds[$iss.id] = $true
    }
}

$remaining = $issues | Where-Object { -not $closeIds.ContainsKey($_.id) }

foreach ($grp in ($remaining | Group-Object project)) {
    $sorted = @($grp.Group | Sort-Object events)
    if ($sorted.Count -lt 5) {
        $sorted | ForEach-Object { $reviewList.Add($_) }
        continue
    }
    $median = $sorted[[int]($sorted.Count / 2)].events
    $q3     = $sorted[[int]($sorted.Count * 0.75)].events
    foreach ($iss in $sorted) {
        if ($iss.events -ge $q3)         { $actList.Add($iss) }
        elseif ($iss.events -ge $median) { $watchList.Add($iss) }
        else                             { $reviewList.Add($iss) }
    }
}

# --- Output ---
function Write-Bucket ($Name, $Items, $Color) {
    if (-not $Items -or @($Items).Count -eq 0) { return }
    $sorted = @($Items | Sort-Object events -Descending)
    Write-Host ''
    Write-Host "=== $Name ($($sorted.Count)) ===" -ForegroundColor $Color
    foreach ($iss in $sorted) {
        $d     = if ($null -ne $iss.delta) { if ($iss.delta -ge 0) { "+$($iss.delta)" } else { "$($iss.delta)" } } else { 'new' }
        $flags = if ($iss.isNew) { ' [NEW]' } elseif ($iss.isRegr) { ' [REGRESSION]' } else { '' }
        $proj  = $iss.project -replace '^zng-', ''
        $fs    = $iss.firstSeen.ToString('MM/dd')
        $ls    = $iss.lastSeen.ToString('MM/dd')
        Write-Host ('  {0,5} {1,6}  u:{2,-3}  [{3}]  {4}->{5}{6}  {7}' -f $iss.events, $d, $iss.users, $proj, $fs, $ls, $flags, $iss.title)
        Write-Host "         $($iss.url)" -ForegroundColor DarkGray
    }
}

Write-Bucket 'ACT'    $actList    'Red'
Write-Bucket 'WATCH'  $watchList  'Yellow'
Write-Bucket 'REVIEW' $reviewList 'Cyan'
Write-Bucket 'CLOSE'  $closeList  'DarkGray'

Write-Host ''
Write-Host "Total: $($issues.Count) issues across $($slugs.Count) projects" -ForegroundColor DarkGray

# --- Atomic snapshot save ---
$newSnap = @{}
foreach ($iss in $issues) { $newSnap[$iss.id] = $iss.events }
$tmpPath = "$snapshotPath.tmp"
$newSnap | ConvertTo-Json | Out-File -FilePath $tmpPath -Encoding utf8
Move-Item -Path $tmpPath -Destination $snapshotPath -Force
```

## After the script runs

One-line summary: `ACT: X | WATCH: X | REVIEW: X | CLOSE: X`.

Then analyze the results and present options via AskUserQuestion:
- Bundle issues that are related (same screen, same error class, same feature area) into a single option.
- Each option = one thing to work on (a single issue or a logical bundle of 2-3).
- Add a "Nothing for now" option.
- Max 4 options total.
- Label each option with the issue title(s) and event count so Joe can skim without re-reading the table.

Example option labels:
- "Fix null-check crash on loan-application (21 events)"
- "Investigate LateInitializationError + GoRouter crash (14 + 5 events, both app-init)"
- "Close WKWebView noise (1 event, benign iOS)"
- "Nothing for now"
