<#
.SYNOPSIS
Full Sentry triage run across the ZNG projects, fetches unresolved issues,
buckets them ACT/WATCH/REVIEW/CLOSE, tracks event-count delta from the last
snapshot, and writes a new snapshot.

.DESCRIPTION
Config (hardcoded, matches the sentry skill's documented values):
- Snapshot: $env:USERPROFILE\.claude\.sentry_snapshot.json
- Token: $env:SENTRY_AUTH_TOKEN (User scope)
- Org: zirtue-nk
- Projects: zng-app, zng-admin, zng-biller

Invoked verbatim by the sentry skill, do not regenerate inline.
#>

$ErrorActionPreference = 'Stop'

$token = [Environment]::GetEnvironmentVariable('SENTRY_AUTH_TOKEN', 'User')
if (-not $token) { $token = $env:SENTRY_AUTH_TOKEN }
if (-not $token) { Write-Error 'SENTRY_AUTH_TOKEN not set'; exit 1 }

$headers = @{ Authorization = "Bearer $token" }
$base    = 'https://sentry.io/api/0'
$org     = 'zirtue-nk'
$targets = @('zng-app', 'zng-admin', 'zng-biller')

# Absolute ACT floor - starting guess, not derived. Revisit against real
# snapshot data if it over/under-fires in practice.
$ActFloorEvents = 25
$ActFloorUsers  = 5

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

# --- Fetch issues (follows the Link `rel="next"` cursor past the first page) ---
function Get-NextPageUrl($linkHeader) {
    if (-not $linkHeader) { return $null }
    foreach ($part in ($linkHeader -split ',(?=\s*<)')) {
        if ($part -match 'rel="next"' -and $part -match 'results="true"' -and $part -match '<([^>]+)>') {
            return $matches[1]
        }
    }
    return $null
}

$now    = Get-Date
$issues = [System.Collections.Generic.List[PSCustomObject]]::new()

foreach ($slug in $slugs) {
    $url       = "$base/projects/$org/$slug/issues/?query=is:unresolved&sort=date&limit=100"
    $pageCount = 0
    $projCount = 0
    while ($url -and $pageCount -lt 10 -and $projCount -lt 1000) {
        $pageCount++
        try {
            $resp = Invoke-WebRequest -UseBasicParsing -Uri $url -Headers $headers
        } catch {
            Write-Host "WARN: $slug - $($_.Exception.Message)" -ForegroundColor Yellow
            break
        }
        $page = $resp.Content | ConvertFrom-Json
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
                isRegr    = ($iss.substatus -eq 'regressed')
            })
            $projCount++
        }
        $url = Get-NextPageUrl $resp.Headers['Link']
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
        foreach ($iss in $sorted) {
            if ($iss.events -ge $ActFloorEvents -or $iss.users -ge $ActFloorUsers -or $iss.isRegr) { $actList.Add($iss) }
            else { $reviewList.Add($iss) }
        }
        continue
    }
    $median = $sorted[[int]($sorted.Count / 2)].events
    $q3     = $sorted[[int]($sorted.Count * 0.75)].events
    foreach ($iss in $sorted) {
        $absFloor = ($iss.events -ge $ActFloorEvents -or $iss.users -ge $ActFloorUsers -or $iss.isRegr)
        if ($iss.events -ge $q3 -or $absFloor) { $actList.Add($iss) }
        elseif ($iss.events -ge $median)       { $watchList.Add($iss) }
        else                                   { $reviewList.Add($iss) }
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
