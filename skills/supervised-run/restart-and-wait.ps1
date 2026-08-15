<#
.SYNOPSIS
  Restart (or reload) a server_supervisor entry and wait for its readiness marker.

.DESCRIPTION
  Wraps the restart+poll dance from this skill's "Wait for readiness" section into
  one call, instead of hand-writing a curl+poll loop per verification (todo 306:
  repeated ~10x by hand in a single zng flutter-web session).

  Flutter entries get /reload (fast hot-restart, matches sv.ps1 ensure -Restart);
  everything else gets /restart. Pass -NoRestart to just wait on an entry you
  already started/restarted yourself.

.PARAMETER Id
  Proc id, form "<project>:<name>" (see sv.ps1 ls).

.PARAMETER Marker
  Substring to wait for in log lines appended after this call starts. Defaults to
  the flutter web-server readiness line when the entry's kind is flutter; required
  for any other kind since there is no universal "ready" line to guess.

.PARAMETER TimeoutSec
  Max seconds to poll. Default 120 - a cold DDC compile can run long.

.PARAMETER NoRestart
  Skip the restart/reload call, just poll logs for the marker (use right after your
  own sv.ps1 ensure/start).

.EXAMPLE
  restart-and-wait.ps1 -Id zng-admin:flutter-run
  restart-and-wait.ps1 -Id my-app:dev -Marker "listening on" -TimeoutSec 60
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Id,

    [string]$Marker,
    [int]$TimeoutSec = 120,
    [switch]$NoRestart
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_common.ps1')

function Fail($msg) {
    Write-Host "ERROR: $msg"
    exit 1
}

$cfg = Get-SupervisorConfig
if (-not $cfg) { Fail "supervisor config not found under $dataDir - is server_supervisor running?" }
try {
    $health = Invoke-WebRequest -Uri "$($cfg.BaseUrl)/health" -UseBasicParsing -TimeoutSec 5
    if ($health.StatusCode -ne 200) { throw "unhealthy" }
}
catch {
    Fail "supervisor not reachable at $($cfg.BaseUrl) - fall back to a plain shell run."
}

$proc = (Invoke-Api $cfg 'GET' '/procs') | Where-Object { $_.id -eq $Id }
if (-not $proc) { Fail "no proc with id '$Id' - check 'sv.ps1 ls'." }

if (-not $Marker) {
    if ($proc.kind -eq 'flutter') { $Marker = 'serving at http://localhost' }
    else { Fail "-Marker is required for kind '$($proc.kind)' (only flutter has a default)." }
}

# High-water mark: only entries appended after this point count as "fresh", so a
# marker left over from before the restart can never false-positive readiness.
# Anchored on the last pre-restart line's TEXT, not on a count: a capped ring
# buffer that is already full keeps Count pinned while its contents shift.
$before = @(Invoke-Api $cfg 'GET' "/procs/$Id/logs")
$anchor = if ($before.Count -gt 0) { $before[$before.Count - 1].text } else { $null }

if (-not $NoRestart) {
    if ($proc.kind -eq 'flutter') { Invoke-Api $cfg 'POST' "/procs/$Id/reload" | Out-Null }
    else { Invoke-Api $cfg 'POST' "/procs/$Id/restart" | Out-Null }
}

$deadline = (Get-Date).AddSeconds($TimeoutSec)
$proxyUrl = $null
while ((Get-Date) -lt $deadline) {
    $logs = @(Invoke-Api $cfg 'GET' "/procs/$Id/logs")
    # Find the anchor's LAST occurrence; everything after it arrived since baseline.
    # No anchor, or rotated past it, means every line present is fresh.
    $cut = -1
    if ($anchor -ne $null) {
        for ($i = $logs.Count - 1; $i -ge 0; $i--) {
            if ($logs[$i].text -eq $anchor) { $cut = $i; break }
        }
        if ($cut -lt 0) { $fresh = $logs }
        elseif ($cut -lt $logs.Count - 1) { $fresh = $logs[($cut + 1)..($logs.Count - 1)] }
        else { $fresh = @() }
    }
    else { $fresh = $logs }

    foreach ($entry in $fresh) {
        if (-not $proxyUrl -and $entry.text -match 'live-reload proxy on ([\d.]+:\d+)') {
            $proxyUrl = "http://$($Matches[1])"
        }
        if ($entry.text -match [regex]::Escape($Marker)) {
            $msg = "$Id ready (matched '$Marker')"
            if ($proxyUrl) { $msg += " - proxy: $proxyUrl" }
            Write-Host $msg
            exit 0
        }
    }
    Start-Sleep -Seconds 2
}

Write-Host "ERROR: $Id did not show marker '$Marker' within ${TimeoutSec}s. Last 10 log lines:"
$logs = @(Invoke-Api $cfg 'GET' "/procs/$Id/logs")
$logs | Select-Object -Last 10 | ForEach-Object { Write-Host "[$($_.stream)] $($_.text)" }
exit 1
