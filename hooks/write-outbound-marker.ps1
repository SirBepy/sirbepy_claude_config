<#
.SYNOPSIS
  Writes the outbound-ground-check marker to hooks/.outbound-marker-<guid>.
.DESCRIPTION
  Single source of truth for the outbound marker path (todo 800): a raw
  `New-Item -Path ...\.claude\hooks\...` call site trips up in auto mode with
  nobody to answer the resulting ask, the same way a hand-built session-marker
  path once landed malformed (todo 365). This script owns the join and guid
  generation and refuses to write anything malformed instead of silently
  producing a stray file, mirroring hooks/write-session-marker.ps1's shape.
.PARAMETER Kind
  Which consuming guard family the marker is for. Defaults to 'outbound', the
  current name every new call site should use. 'shortcut' remains only for the
  legacy `.shortcut-marker*` name the two Shortcut guards still accept.
#>
[CmdletBinding()]
param(
    [ValidateSet('outbound', 'shortcut')]
    [string]$Kind = 'outbound'
)

$ErrorActionPreference = 'Stop'

$guid = [guid]::NewGuid().ToString('N')
$markerName = ".$Kind-marker-$guid"

if ($markerName -notmatch '^\.(outbound|shortcut)-marker-[0-9a-f]{32}$') {
    throw "write-outbound-marker.ps1: generated marker name '$markerName' failed validation - refusing to write a malformed marker."
}

$markerPath = Join-Path $PSScriptRoot $markerName
New-Item -ItemType File -Path $markerPath -Force | Out-Null

Write-Output "Outbound marker written: $markerPath"
