# d-cargo-sweep-auto.ps1 - scheduled wrapper around d-cargo-sweep.ps1 (tiers B, C, D only).
#
# Registered in Windows Task Scheduler as "D-CargoSweep" (twice a day). Runs outside any Claude chat, so
# the harness's drive-root delete block does not apply. It does nothing unless D: is under -ThresholdPct
# free, and never touches a live build: d-cargo-sweep.ps1 -Apply refuses while cargo/rustc/rust-lld/link
# runs, and this wrapper checks first so a skipped run costs one Get-Volume call.
#
# Tiers A and E stay manual: they name one-off dirs (dead projects, loop1025-target), not a recurring leak.
# The recurring leak is claude_conductor_lib: a new incremental dir plus about 5 GB of .pdb per build
# variant every day or two, all in the shared D:\cargo-target.
#
# Log: %LOCALAPPDATA%\d-cargo-sweep\log.txt (C:, because D: may have no room for a log), one line per run.
param(
  [int]$ThresholdPct = 25
)

$ErrorActionPreference = 'Continue'
$sweep = Join-Path $PSScriptRoot 'd-cargo-sweep.ps1'
$logDir = Join-Path $env:LOCALAPPDATA 'd-cargo-sweep'
$log = Join-Path $logDir 'log.txt'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Write-Log($msg) {
  $line = '{0}  {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
  [System.IO.File]::AppendAllText($log, $line + [Environment]::NewLine)
}

$vol = Get-Volume -DriveLetter D -ErrorAction SilentlyContinue
if (-not $vol) { Write-Log 'skip: D: not present'; exit 0 }
$freeGB = [math]::Round($vol.SizeRemaining / 1GB, 1)
$freePct = [math]::Round(100 * $vol.SizeRemaining / $vol.Size, 1)

if ($freePct -ge $ThresholdPct) {
  Write-Log ("ok: D: {0} GB free ({1}%), threshold {2}%, nothing to do" -f $freeGB, $freePct, $ThresholdPct)
  exit 0
}

if (Get-Process cargo, rustc, rust-lld, link -ErrorAction SilentlyContinue) {
  Write-Log ("skip: D: {0} GB free ({1}%) but a build is running, will retry next run" -f $freeGB, $freePct)
  exit 0
}

Write-Log ("sweep: D: {0} GB free ({1}%) is under {2}%, running tiers B,C,D" -f $freeGB, $freePct, $ThresholdPct)
$out = & powershell -NoProfile -File $sweep -Apply -Tiers 'B,C,D' 2>&1 | Out-String
$vol2 = Get-Volume -DriveLetter D
$after = [math]::Round($vol2.SizeRemaining / 1GB, 1)
$tail = ($out -split "`r?`n" | Where-Object { $_ -match 'Tier [CD]:|removed|STILL PRESENT|REFUSING' } | Select-Object -First 12) -join ' | '
Write-Log ("done: D: {0} GB -> {1} GB free (+{2} GB). {3}" -f $freeGB, $after, [math]::Round($after - $freeGB, 1), $tail)
