<#
.SYNOPSIS
Fetch Sentry issue + latest event details by URL or issue ID.

.DESCRIPTION
Hits Sentry REST API and prints a compact summary: title, culprit, tags,
breadcrumbs (last N), exception type/value, top stack frames (app frames only).

Requires env var SENTRY_AUTH_TOKEN (user-scope).

.PARAMETER UrlOrId
A full Sentry issue URL (e.g. https://zirtue-nk.sentry.io/issues/7479592682/...),
a bare numeric issue ID, or a short id shown in the Sentry UI (e.g. ZNG-APP-2X).
Short ids are resolved via the shortIDLookup API before continuing.

.PARAMETER Org
Org slug. Optional if URL is given (parsed from subdomain).

.PARAMETER Frames
Number of stack frames to print (default 10).

.PARAMETER Breadcrumbs
Number of breadcrumbs to print (default 10).

.PARAMETER Raw
Dump raw JSON for event + issue instead of formatted summary.

.EXAMPLE
Get-SentryIssue 'https://zirtue-nk.sentry.io/issues/7479592682/'
.EXAMPLE
Get-SentryIssue 7479592682 -Org zirtue-nk -Frames 20
.EXAMPLE
Get-SentryIssue ZNG-APP-2X -Org zirtue-nk
#>
param(
  [Parameter(Mandatory=$true, Position=0)]
  [string]$UrlOrId,
  [string]$Org,
  [int]$Frames = 10,
  [int]$Breadcrumbs = 10,
  [switch]$Raw
)

$ErrorActionPreference = 'Stop'

$token = $env:SENTRY_AUTH_TOKEN
if (-not $token) {
  $token = [Environment]::GetEnvironmentVariable('SENTRY_AUTH_TOKEN','User')
}
if (-not $token) {
  Write-Error 'SENTRY_AUTH_TOKEN env var not set. Set with: [Environment]::SetEnvironmentVariable("SENTRY_AUTH_TOKEN","<token>","User")'
  exit 1
}

$headers = @{ Authorization = "Bearer $token" }
$base = 'https://sentry.io/api/0'

# Parse URL, bare numeric ID, or short id (e.g. ZNG-APP-2X: letters/digits/hyphens, not purely numeric)
$issueId = $null
if ($UrlOrId -match '^\d+$') {
  $issueId = $UrlOrId
} elseif ($UrlOrId -match 'https?://([^.]+)\.sentry\.io/(?:.*?/)?issues/(\d+)') {
  if (-not $Org) { $Org = $Matches[1] }
  $issueId = $Matches[2]
} elseif ($UrlOrId -match '^[A-Za-z0-9]+(-[A-Za-z0-9]+)+$') {
  if (-not $Org) {
    Write-Error 'Org slug required when passing a short id. Use -Org <slug>.'
    exit 1
  }
  try {
    $shortIdResp = Invoke-WebRequest -Uri "$base/organizations/$Org/shortids/$UrlOrId/" -Headers $headers -Method Get -UseBasicParsing
    $shortIdData = $shortIdResp.Content | ConvertFrom-Json
  } catch {
    Write-Error "Short id lookup failed for $UrlOrId : $($_.Exception.Message)"
    exit 1
  }
  $issueId = $shortIdData.group.id
} else {
  Write-Error "Could not parse URL, issue ID, or short id from: $UrlOrId"
  exit 1
}

if (-not $Org) {
  Write-Error 'Org slug required when passing bare ID. Use -Org <slug>.'
  exit 1
}

try {
  $issue = Invoke-RestMethod -Uri "$base/organizations/$Org/issues/$issueId/" -Headers $headers -Method Get
  $eventData = Invoke-RestMethod -Uri "$base/organizations/$Org/issues/$issueId/events/latest/" -Headers $headers -Method Get
} catch {
  Write-Error "API call failed: $($_.Exception.Message)"
  if ($_.Exception.Response) {
    $stream = $_.Exception.Response.GetResponseStream()
    $reader = New-Object System.IO.StreamReader($stream)
    Write-Host $reader.ReadToEnd()
  }
  exit 1
}

if ($Raw) {
  [pscustomobject]@{ issue = $issue; event = $eventData } | ConvertTo-Json -Depth 20
  return
}

Write-Host ''
Write-Host "=== ISSUE $issueId ===" -ForegroundColor Cyan
Write-Host "Title:       $($issue.title)"
Write-Host "Culprit:     $($issue.culprit)"
Write-Host "Level:       $($issue.level)"
Write-Host "Status:      $($issue.status)"
Write-Host "Platform:    $($issue.platform)"
Write-Host "Project:     $($issue.project.slug)"
Write-Host "First seen:  $($issue.firstSeen)"
Write-Host "Last seen:   $($issue.lastSeen)"
Write-Host "Count:       $($issue.count)  Users: $($issue.userCount)"
Write-Host "Permalink:   $($issue.permalink)"

Write-Host ''
Write-Host '--- Tags ---' -ForegroundColor Cyan
foreach ($t in $eventData.tags) {
  Write-Host ("  {0,-20} {1}" -f $t.key, $t.value)
}

# Exception
$excEntry = $eventData.entries | Where-Object { $_.type -eq 'exception' } | Select-Object -First 1
if ($excEntry) {
  Write-Host ''
  Write-Host '--- Exception ---' -ForegroundColor Cyan
  foreach ($exc in $excEntry.data.values) {
    Write-Host "Type:    $($exc.type)"
    Write-Host "Value:   $($exc.value)"
    if ($exc.module) { Write-Host "Module:  $($exc.module)" }
    if ($exc.stacktrace -and $exc.stacktrace.frames) {
      $allFrames = $exc.stacktrace.frames
      # Sentry orders frames bottom-up (oldest first); reverse for readability
      $ordered = @($allFrames) ; [array]::Reverse($ordered)
      $appFrames = $ordered | Where-Object { $_.inApp -eq $true }
      $show = if ($appFrames.Count -gt 0) { $appFrames } else { $ordered }
      $show = $show | Select-Object -First $Frames
      Write-Host ''
      Write-Host '  Stack (top -> bottom, inApp prioritized):'
      foreach ($f in $show) {
        $loc = if ($f.filename) { "$($f.filename):$($f.lineNo)" } else { '<unknown>' }
        $fn = if ($f.function) { $f.function } else { '<anonymous>' }
        $marker = if ($f.inApp) { '*' } else { ' ' }
        Write-Host ("  {0} {1}  ({2})" -f $marker, $fn, $loc)
        if ($f.context) {
          foreach ($ctx in $f.context) {
            $lineNo = $ctx[0]; $code = $ctx[1]
            if ($lineNo -eq $f.lineNo) {
              Write-Host ("      >> {0,4}: {1}" -f $lineNo, $code) -ForegroundColor Yellow
            }
          }
        }
      }
    }
  }
}

# Breadcrumbs
$crumbEntry = $eventData.entries | Where-Object { $_.type -eq 'breadcrumbs' } | Select-Object -First 1
if ($crumbEntry) {
  Write-Host ''
  Write-Host '--- Breadcrumbs (most recent last) ---' -ForegroundColor Cyan
  $crumbs = $crumbEntry.data.values | Select-Object -Last $Breadcrumbs
  foreach ($c in $crumbs) {
    $msg = if ($c.message) { $c.message } elseif ($c.data) { ($c.data | ConvertTo-Json -Compress -Depth 3) } else { '' }
    Write-Host ("  [{0}] {1,-10} {2,-12} {3}" -f $c.timestamp, $c.level, $c.category, $msg)
  }
}

# Request
$reqEntry = $eventData.entries | Where-Object { $_.type -eq 'request' } | Select-Object -First 1
if ($reqEntry) {
  Write-Host ''
  Write-Host '--- Request ---' -ForegroundColor Cyan
  Write-Host "URL:    $($reqEntry.data.url)"
  Write-Host "Method: $($reqEntry.data.method)"
}

# User
if ($eventData.user) {
  Write-Host ''
  Write-Host '--- User ---' -ForegroundColor Cyan
  Write-Host "Id:    $($eventData.user.id)"
  Write-Host "Email: $($eventData.user.email)"
}

Write-Host ''
