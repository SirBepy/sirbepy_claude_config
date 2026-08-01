param(
  [Parameter(Mandatory=$true)][string]$RepoPath,
  [Parameter(Mandatory=$true)][string]$TaskName,
  [string]$TaskPath = "\ClaudeCronRun\",
  [string]$ClaudeExe = ""
)

# /cron-run wrapper. Launched by a Windows Scheduled Task. One firing = one tick.
# The wrapper owns: working dir, logging, a re-entrancy lock, and the reliable
# teardown (it, not the LLM, unregisters the task when the queue is drained).
# Invoked WITHOUT -NoProfile so the PS profile sets PATH (git/fvm/flutter), but
# WITH -ExecutionPolicy Bypass so this unsigned file runs.

$ErrorActionPreference = "Stop"

# Resolve claude.exe from PATH first (keeps working if the install path moves);
# fall back to the known-good literal path if PATH resolution fails.
if (-not $ClaudeExe) {
  $resolvedClaude = (Get-Command claude -ErrorAction SilentlyContinue).Source
  $ClaudeExe = if ($resolvedClaude) { $resolvedClaude } else { "C:\Users\tecno\.local\bin\claude.exe" }
}

$logDir = Join-Path $RepoPath "docs\night_run\logs"
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Force -Path $logDir | Out-Null }
$stamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$log   = Join-Path $logDir ("tick_" + $stamp + ".log")
function Log($m) { Add-Content -Path $log -Value ("[" + (Get-Date -Format "HH:mm:ss") + "] " + $m) -Encoding utf8 }

# Heartbeat: written at START, so a tick that dies mid-run still leaves a marker.
$heartbeat = Join-Path $RepoPath "docs\night_run\heartbeat.log"
Add-Content -Path $heartbeat -Value ("[" + $stamp + "] tick start (task=$TaskName)") -Encoding utf8

# Re-entrancy lock (layer 2; Task Scheduler IgnoreNew is layer 1, INDEX soft-lock is layer 3).
# Timeout mirrors the INDEX soft-lock's own reclaim window (ceil(interval * 1.25), see
# SKILL.md Tick mode step 1) instead of a fixed 60m, so the two layers agree on staleness
# even at short intervals (a 30m interval used to leave a 38-60m window where this lock
# outlived the INDEX reclaim and wrongly skipped the tick).
$lockTimeoutMinutes = 60
$indexPath = Join-Path $RepoPath "docs\night_run\INDEX.md"
if (Test-Path $indexPath) {
  $intervalLine = Get-Content -Path $indexPath | Where-Object { $_ -match '^Interval:\s*(\d+)\s*(m|min|h|hr)' } | Select-Object -First 1
  if ($intervalLine -match '^Interval:\s*(\d+)\s*(m|min|h|hr)') {
    $intervalMinutes = if ($Matches[2] -in @('h', 'hr')) { [int]$Matches[1] * 60 } else { [int]$Matches[1] }
    $lockTimeoutMinutes = [math]::Ceiling($intervalMinutes * 1.25)
  }
}
$lock = Join-Path $RepoPath "docs\night_run\.tick.lock"
if (Test-Path $lock) {
  $age = (Get-Date) - (Get-Item $lock).LastWriteTime
  if ($age.TotalMinutes -lt $lockTimeoutMinutes) { Log "SKIP: tick lock held (age $([int]$age.TotalMinutes)m, timeout ${lockTimeoutMinutes}m)"; exit 0 }
  Log "reclaimed stale lock (age $([int]$age.TotalMinutes)m, timeout ${lockTimeoutMinutes}m)"
}
Set-Content -Path $lock -Value $PID -Encoding utf8

$allDone = $false
try {
  Set-Location -Path $RepoPath
  Log "START repo=$RepoPath user=$(whoami)"
  $gitSrc = (Get-Command git -ErrorAction SilentlyContinue).Source
  Log "git on PATH: $gitSrc"
  if (-not $gitSrc) { Log "FATAL: git not on PATH (profile not loaded?). Aborting tick." ; throw "git missing" }

  # Headless tick. acceptEdits + the user's permissions.allow list; the tick body
  # uses raw git + pre-allowed commands so it does not stall on a permission prompt.
  $out = & $ClaudeExe -p "/cron-run tick" --permission-mode acceptEdits --no-session-persistence 2>&1 | Out-String
  Log "claude exit=$LASTEXITCODE"
  Add-Content -Path $log -Value "----- claude output -----" -Encoding utf8
  Add-Content -Path $log -Value $out -Encoding utf8
  Add-Content -Path $log -Value "----- end output -----" -Encoding utf8

  if ($out -match "CRON_RUN_ALL_DONE") { $allDone = $true; Log "sentinel CRON_RUN_ALL_DONE seen" }
}
catch { Log ("WRAPPER ERROR: " + $_.Exception.Message) }
finally { Remove-Item -Path $lock -Force -ErrorAction SilentlyContinue }

# Wrapper-driven teardown: far more reliable than asking the LLM to remember.
if ($allDone) {
  try {
    Unregister-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Confirm:$false -ErrorAction Stop
    Log "task '$TaskName' unregistered (queue drained)"
    Add-Content -Path $heartbeat -Value ("[" + (Get-Date -Format "yyyy-MM-dd_HH-mm-ss") + "] queue drained; task removed") -Encoding utf8
  }
  catch { Log ("unregister failed: " + $_.Exception.Message) }
}
