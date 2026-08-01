# schedule-once.ps1 — registrar for /schedule-once.
# Writes a job sidecar + registers a single-fire, self-deleting Windows Scheduled Task.
# The wrapper (run-once.ps1) reads the sidecar by task name, so an arbitrary prompt
# never has to be quoted into the task action string.

param(
    [Parameter(Mandatory = $true)][string]$At,          # absolute datetime, e.g. "2026-06-07 15:30:00"
    [Parameter(Mandatory = $true)][string]$WorkDir,     # dir the job runs in
    [string]$Prompt,                                    # a Claude prompt to run via `claude -p`
    [string]$Shell,                                     # OR a raw PowerShell command to run
    [ValidateSet('acceptEdits', 'bypassPermissions', 'default', 'plan')]
    [string]$PermMode = 'acceptEdits',
    [string]$Model = '',                                # optional model override (opus/sonnet/fable or full id)
    [ValidateSet('', 'low', 'medium', 'high', 'xhigh', 'max')]
    [string]$Effort = '',                               # optional reasoning-effort override
    [string]$Label = ''                                 # optional friendly slug source
)

$ErrorActionPreference = 'Stop'

if (-not $Prompt -and -not $Shell) { throw "Provide -Prompt or -Shell." }
if ($Prompt -and $Shell) { throw "Provide only one of -Prompt / -Shell." }

# Parse + validate the fire time is in the future.
try { $fireAt = [datetime]::Parse($At) } catch { throw "Could not parse -At '$At' as a datetime." }
if ($fireAt -le (Get-Date)) { throw "Fire time '$fireAt' is not in the future (now is $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss'))." }

# Collision-proof task name: ClaudeOnce_<slug>_<fire-stamp>.
$slugSrc = if ($Label) { $Label } elseif ($Prompt) { $Prompt } else { $Shell }
$slug = ($slugSrc -replace '[^A-Za-z0-9]+', '-').Trim('-')
if ($slug.Length -gt 30) { $slug = $slug.Substring(0, 30) }
if (-not $slug) { $slug = 'job' }
$taskName = "ClaudeOnce_${slug}_$($fireAt.ToString('yyyyMMdd-HHmmss'))"

# Resolve claude.exe now (env is known-good at schedule time) for prompt jobs.
$claudeExe = ''
if ($Prompt) {
    $claudeExe = (Get-Command claude -ErrorAction SilentlyContinue).Source
    if (-not $claudeExe) { throw "claude executable not found on PATH; cannot schedule a prompt run (use -Shell for a raw command)." }
}

# Persist the job spec.
$base    = Join-Path $env:LOCALAPPDATA 'ClaudeScheduleOnce'
$jobsDir = Join-Path $base 'jobs'
New-Item -ItemType Directory -Force -Path $jobsDir | Out-Null
$jobFile = Join-Path $jobsDir "$taskName.json"

$job = [ordered]@{
    taskName  = $taskName
    mode      = if ($Prompt) { 'prompt' } else { 'shell' }
    payload   = if ($Prompt) { $Prompt } else { $Shell }
    workDir   = $WorkDir
    permMode  = $PermMode
    model     = $Model
    effort    = $Effort
    claudeExe = $claudeExe
    humanTime = $fireAt.ToString('yyyy-MM-dd HH:mm:ss')
    createdAt = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss')
}
($job | ConvertTo-Json) | Out-File -FilePath $jobFile -Encoding utf8

# Register a single-fire task. -StartWhenAvailable runs it on wake if the PC was asleep at fire time.
$wrapper   = Join-Path $PSScriptRoot 'run-once.ps1'
$action    = New-ScheduledTaskAction -Execute 'powershell.exe' `
    -Argument ('-ExecutionPolicy Bypass -WindowStyle Hidden -File "' + $wrapper + '" -TaskName "' + $taskName + '"')
$trigger   = New-ScheduledTaskTrigger -Once -At $fireAt
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $taskName -TaskPath '\ClaudeOnce\' `
    -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
    -Description "Claude schedule-once. Fires once at $($job.humanTime), then self-deletes. Safe to delete." -Force | Out-Null

[PSCustomObject]@{
    TaskName = $taskName
    FiresAt  = $job.humanTime
    Mode     = $job.mode
    Model    = if ($Model) { $Model } else { '(default)' }
    Effort   = if ($Effort) { $Effort } else { '(default)' }
    WorkDir  = $WorkDir
    LogFile  = (Join-Path $base "logs\$taskName.log")
    JobFile  = $jobFile
} | Format-List
