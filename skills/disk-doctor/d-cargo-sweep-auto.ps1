# d-cargo-sweep-auto.ps1 - scheduled wrapper around d-cargo-sweep.ps1 (tiers B and D only).
#
# Registered in Windows Task Scheduler as "D-CargoSweep" (twice a day). Runs outside any Claude chat, so
# the harness's drive-root delete block does not apply. It does nothing unless D: is under -ThresholdPct
# free, and never touches a live build: d-cargo-sweep.ps1 -Apply refuses while cargo/rustc/rust-lld/link
# runs, and this wrapper checks first so a skipped run costs one Get-Volume call.
#
# Tiers A and E stay manual: they name one-off dirs (dead projects, loop1025-target), not a recurring leak.
# Tier C (old .rcgu.o) stays manual too: rustc can regenerate those objects when it rebuilds the crate,
# so deleting them automatically trades disk space for rebuild time (Joe, 2026-11-04).
# B removes aged incremental cache dirs: a new build recreates them, so the cost is rebuild time only.
# D removes superseded variants of our own test/lib binaries, which a new build never rewrites.
# The recurring leak is claude_conductor_lib: a new incremental dir plus about 5 GB of .pdb per build
# variant every day or two, all in the shared D:\cargo-target.
#
# Log: %LOCALAPPDATA%\d-cargo-sweep\log.txt (C:, because D: may have no room for a log), one line per run.
# The line starts with ok / skip / sweep / done / refused / aborted / failed, so a run that did not sweep
# never reads as done. The wrapper exits with the child's code (3 refused, 4 aborted mid-sweep), which
# Task Scheduler shows as the task's last result.
# The last four parameters exist so test_d_cargo_sweep_auto.ps1 can run the wrapper against a stub
# sweep on another drive; the scheduled task passes none of them.
param(
  [int]$ThresholdPct = 25,
  [string]$Drive = 'D',
  [string]$SweepScript = (Join-Path $PSScriptRoot 'd-cargo-sweep.ps1'),
  [string]$LogDir = (Join-Path $env:LOCALAPPDATA 'd-cargo-sweep'),
  [string[]]$BuildProcesses = @('cargo', 'rustc', 'rust-lld', 'link')
)

$ErrorActionPreference = 'Continue'
$sweep = $SweepScript
$logDir = $LogDir
$log = Join-Path $logDir 'log.txt'
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Write-Log($msg) {
  $line = '{0}  {1}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $msg
  [System.IO.File]::AppendAllText($log, $line + [Environment]::NewLine)
}

$vol = Get-Volume -DriveLetter $Drive -ErrorAction SilentlyContinue
if (-not $vol) { Write-Log "skip: ${Drive}: not present"; exit 0 }
$freeGB = [math]::Round($vol.SizeRemaining / 1GB, 1)
$freePct = [math]::Round(100 * $vol.SizeRemaining / $vol.Size, 1)

if ($freePct -ge $ThresholdPct) {
  Write-Log ("ok: D: {0} GB free ({1}%), threshold {2}%, nothing to do" -f $freeGB, $freePct, $ThresholdPct)
  exit 0
}

if (Get-Process $BuildProcesses -ErrorAction SilentlyContinue) {
  Write-Log ("skip: D: {0} GB free ({1}%) but a build is running, will retry next run" -f $freeGB, $freePct)
  exit 0
}

Write-Log ("sweep: D: {0} GB free ({1}%) is under {2}%, running tiers B,D" -f $freeGB, $freePct, $ThresholdPct)
# The host that runs this wrapper also runs the sweep: powershell.exe under the task, whatever PATH holds
# is never consulted.
$hostExe = (Get-Process -Id $PID).Path
$out = & $hostExe -NoProfile -File $sweep -Apply -Tiers 'B,D' 2>&1 | Out-String
$code = $LASTEXITCODE
$vol2 = Get-Volume -DriveLetter $Drive
$after = [math]::Round($vol2.SizeRemaining / 1GB, 1)
$lines = $out -split "`r?`n"
# The child prints one "removed <path>" line per tier A/B/E dir and one "STILL PRESENT <path>" line per
# dir it could not remove, both before its summary. Both are counted so a long run of either cannot
# push the Tier D summary or a refusal out of the capped tail, which keeps only those lines.
$removedDirs = @($lines | Where-Object { $_ -match '^removed ' }).Count
$stillPresent = @($lines | Where-Object { $_ -match '^STILL PRESENT' }).Count
$tail = ($lines | Where-Object { $_ -match '^(Tier D:|REFUSING|ABORT)' } | Select-Object -First 12) -join ' | '
$detail = "{0}: {1} GB -> {2} GB free ({3}{4} GB). {5} dirs removed, {6} still present. {7}" -f $Drive, $freeGB, $after, $(if ($after -ge $freeGB) { '+' } else { '' }), [math]::Round($after - $freeGB, 1), $removedDirs, $stillPresent, $tail
switch ($code) {
  0 { Write-Log "done: $detail" }
  3 { Write-Log "refused (exit 3, a build is running): $detail" }
  4 { Write-Log "aborted (exit 4, a build started mid-sweep): $detail" }
  default { Write-Log "failed (exit $code): $detail" }
}
exit $code
