<#
.SYNOPSIS
  Writes the commit-guard session marker to hooks/.session-markers/<session_id>.
.DESCRIPTION
  Single source of truth for the session-marker path (todo 365): a bare
  string-concat call site once produced `hooks/.session-markers$CLAUDE_CODE_SESSION_ID`
  (missing separator) and `hooks/.session-markers$CLAUDE_CODE_SESSION_ID` (unexpanded
  variable, from a Bash-issued PowerShell recipe). This script owns the join and
  refuses to write anything malformed instead of silently producing a stray file.
.PARAMETER SessionId
  Defaults to $env:CLAUDE_CODE_SESSION_ID. Errors (does not write) if empty, or if
  it still contains a literal '$' - a resolved session id can never contain one, so
  its presence means a shell variable was never expanded before reaching this script.
#>
[CmdletBinding()]
param(
    [string]$SessionId = $env:CLAUDE_CODE_SESSION_ID
)

$ErrorActionPreference = 'Stop'

if ([string]::IsNullOrWhiteSpace($SessionId)) {
    throw "write-session-marker.ps1: CLAUDE_CODE_SESSION_ID is empty - refusing to write a marker with no session id."
}

if ($SessionId.Contains('$')) {
    throw "write-session-marker.ps1: session id '$SessionId' contains a literal '`$' - a shell variable was not expanded before reaching this script. Refusing to write a malformed marker path."
}

$markerDir = Join-Path $PSScriptRoot '.session-markers'
New-Item -ItemType Directory -Force -Path $markerDir | Out-Null

$markerPath = Join-Path $markerDir $SessionId
Set-Content -Path $markerPath -Value 'x'

Write-Output "Session marker written: $markerPath"
