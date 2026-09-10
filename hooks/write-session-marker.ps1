<#
.SYNOPSIS
  Writes the commit-guard session marker to hooks/.session-markers/<session_id>,
  then opportunistically prunes every OTHER session marker whose session is
  provably gone (todo 917).
.DESCRIPTION
  Single source of truth for the session-marker path (todo 365): a bare
  string-concat call site once produced `hooks/.session-markers$CLAUDE_CODE_SESSION_ID`
  (missing separator) and `hooks/.session-markers$CLAUDE_CODE_SESSION_ID` (unexpanded
  variable, from a Bash-issued PowerShell recipe). This script owns the join and
  refuses to write anything malformed instead of silently producing a stray file.

  Pruning (todo 917): a session marker is checked by `.exists()` for the
  entire life of its session, with no freshness window (unlike the legacy
  per-commit `.commit-marker-*` files, which commit-guard.py itself prunes
  by age - see `_marker_pruning.py`). An age threshold here would be a
  guess: a long-running session must not lose its marker just for being
  slow. The only thing that proves a marker safe to delete is that its
  session is provably gone, so pruning is liveness-based, not age-based,
  and runs only at the moment THIS marker is written - never on a schedule,
  never a separate command someone has to remember - because the session
  doing the writing is by definition alive and is already paying the cost
  of this call.

  Liveness source: `~/.claude/sessions/*.json`, one record per currently
  running session (sessionId + pid), the same registry
  `skills/close/rename-session.ps1 -Close`/`-GetId` already trusts as
  authoritative for "is this pid alive". Per todo 60, a raw process-tree
  walk is NOT trustworthy on a machine running many concurrent `claude`
  processes - only a sessionId->pid lookup, verified with `Get-Process -Id`,
  is. A marker is pruned when either:
    - no record in the registry carries its session id at all (the harness
      has no live record of it), or
    - a record does exist but `Get-Process -Id <that pid>` fails (stale
      record; the process already exited).
  Any other marker is left alone, including one this script cannot resolve
  either way (e.g. the registry itself is unreadable) - see
  Remove-DeadSessionMarkers, which treats "not proven live" as distinct
  from "proven dead" only through those two checks, never through absence
  of information.
.PARAMETER SessionId
  Defaults to $env:CLAUDE_CODE_SESSION_ID. Errors (does not write) if empty, or if
  it still contains a literal '$' - a resolved session id can never contain one, so
  its presence means a shell variable was never expanded before reaching this script.
.PARAMETER SessionMarkerDir
  Override for `.session-markers/` - test-only. Defaults to the real path
  next to this script.
.PARAMETER SessionsRegistryDir
  Override for `~/.claude/sessions/` - test-only. Defaults to the real path.
#>
[CmdletBinding()]
param(
    [string]$SessionId = $env:CLAUDE_CODE_SESSION_ID,
    [string]$SessionMarkerDir,
    [string]$SessionsRegistryDir
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($SessionId)) {
    throw "write-session-marker.ps1: CLAUDE_CODE_SESSION_ID is empty - refusing to write a marker with no session id."
}

if ($SessionId.Contains('$')) {
    throw "write-session-marker.ps1: session id '$SessionId' contains a literal '`$' - a shell variable was not expanded before reaching this script. Refusing to write a malformed marker path."
}

if (-not $SessionMarkerDir) {
    $SessionMarkerDir = Join-Path $PSScriptRoot '.session-markers'
}
if (-not $SessionsRegistryDir) {
    $SessionsRegistryDir = Join-Path (Split-Path $PSScriptRoot -Parent) 'sessions'
}

New-Item -ItemType Directory -Force -Path $SessionMarkerDir | Out-Null

$markerPath = Join-Path $SessionMarkerDir $SessionId
Set-Content -Path $markerPath -Value 'x'

Write-Output "Session marker written: $markerPath"

function Remove-DeadSessionMarkers {
    <#
    Deletes every marker in $MarkerDir, other than $OwnSessionId's own, whose
    session id resolves to a provably dead (or provably absent) session in
    $RegistryDir. Returns the number pruned. A per-file delete failure is
    swallowed - a concurrent writer/pruner may have already removed the same
    file, and losing that race is not an error.
    #>
    param(
        [Parameter(Mandatory)] [string]$MarkerDir,
        [Parameter(Mandatory)] [string]$RegistryDir,
        [Parameter(Mandatory)] [string]$OwnSessionId
    )

    if (-not (Test-Path $MarkerDir)) { return 0 }

    # sessionId -> pid for every currently-registered session. A record that
    # fails to parse is skipped outright - never treated as proof of death
    # for whatever marker might otherwise match it.
    $liveBySessionId = @{}
    if (Test-Path $RegistryDir) {
        foreach ($f in (Get-ChildItem -Path $RegistryDir -Filter '*.json' -File -ErrorAction SilentlyContinue)) {
            try {
                $rec = Get-Content -Raw -Path $f.FullName -ErrorAction Stop | ConvertFrom-Json
                if ($rec.sessionId -and $rec.pid) {
                    $liveBySessionId[[string]$rec.sessionId] = [int]$rec.pid
                }
            } catch {
                # Unreadable/malformed record - skip it, don't guess.
            }
        }
    }

    $prunedCount = 0
    foreach ($markerFile in (Get-ChildItem -Path $MarkerDir -File -ErrorAction SilentlyContinue)) {
        $markerSessionId = $markerFile.Name
        if ($markerSessionId -eq $OwnSessionId) { continue }

        $isLive = $false
        if ($liveBySessionId.ContainsKey($markerSessionId)) {
            $ownerPid = $liveBySessionId[$markerSessionId]
            if (Get-Process -Id $ownerPid -ErrorAction SilentlyContinue) {
                $isLive = $true
            }
        }

        if (-not $isLive) {
            try {
                Remove-Item -Path $markerFile.FullName -Force -ErrorAction Stop
                $prunedCount++
            } catch {
                # Lost a race - not an error.
            }
        }
    }
    return $prunedCount
}

$pruned = Remove-DeadSessionMarkers -MarkerDir $SessionMarkerDir -RegistryDir $SessionsRegistryDir -OwnSessionId $SessionId
if ($pruned -gt 0) {
    Write-Output "Pruned $pruned dead session marker(s)."
}
