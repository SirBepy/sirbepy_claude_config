# run-once.ps1 — launched by a Windows Scheduled Task created by /schedule-once.
# Reads the job sidecar for $TaskName, runs it once, logs, then self-deletes
# (unregisters its own task + removes the job file). Fire-and-forget by design.

param(
    [Parameter(Mandatory = $true)][string]$TaskName
)

$ErrorActionPreference = 'Continue'

$base    = Join-Path $env:LOCALAPPDATA 'ClaudeScheduleOnce'
$jobFile = Join-Path $base "jobs\$TaskName.json"
$logDir  = Join-Path $base 'logs'
$logFile = Join-Path $logDir "$TaskName.log"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Log($m) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $m" | Tee-Object -FilePath $logFile -Append | Out-Null
}

# When $false, the finally block keeps the task + sidecar registered (premature
# fire, or a session-limit retry was scheduled) instead of self-deleting.
$selfDelete = $true

try {
    if (-not (Test-Path $jobFile)) { Log "ERROR: job file not found: $jobFile"; return }
    $job = Get-Content -Raw -Path $jobFile | ConvertFrom-Json

    # Premature-fire guard: Task Scheduler has been observed launching pending
    # ClaudeOnce tasks hours early during Modern Standby transitions (2026-07-03,
    # all three pending tasks fired at once). If we are running measurably before
    # the scheduled time, refuse: leave the task registered so the real trigger
    # still fires.
    if ($job.PSObject.Properties['humanTime'] -and $job.humanTime) {
        $scheduledAt = $null
        try { $scheduledAt = [datetime]::ParseExact($job.humanTime, 'yyyy-MM-dd HH:mm:ss', $null) } catch {}
        if ($scheduledAt -and ((Get-Date) -lt $scheduledAt.AddMinutes(-2))) {
            Log "PREMATURE fire: now=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') but scheduled=$($job.humanTime). Skipping run; task stays registered."
            $selfDelete = $false
            return
        }
    }

    Log "START $TaskName  mode=$($job.mode)  workDir=$($job.workDir)"
    if ($job.workDir -and (Test-Path $job.workDir)) { Set-Location -Path $job.workDir }

    if ($job.mode -eq 'prompt') {
        $exe = $job.claudeExe
        if (-not $exe -or -not (Test-Path $exe)) { $exe = (Get-Command claude -ErrorAction SilentlyContinue).Source }
        if (-not $exe) { Log "ERROR: claude executable not found"; return }
        # Build optional overrides. Guard each field so sidecars written before these
        # were added (no model/effort keys) still run exactly as before.
        $extra = @()
        if ($job.PSObject.Properties['model']  -and $job.model)  { $extra += @('--model',  $job.model) }
        if ($job.PSObject.Properties['effort'] -and $job.effort) { $extra += @('--effort', $job.effort) }
        Log "RUN  <prompt via stdin> | claude -p --permission-mode $($job.permMode) $($extra -join ' ')"
        # Pipe the prompt via stdin rather than as an arg — a native-arg prompt mangles
        # embedded quotes. -p reads stdin as the prompt (see `claude --help`: "useful for pipes").
        $claudeOut = $job.payload | & $exe -p --permission-mode $job.permMode @extra --no-session-persistence *>&1 |
            Tee-Object -FilePath $logFile -Append
        $claudeExit = $LASTEXITCODE
        Log "claude exit code: $claudeExit"

        # Session-limit retry: a limit-hit at fire time used to burn the one-shot
        # (run fails, task self-deletes, work never happens). Instead, push the
        # trigger past the stated reset and keep the task alive. Capped retries so
        # a permanently-failing job cannot loop forever.
        $outText = ($claudeOut | Out-String)
        if ($claudeExit -ne 0 -and $outText -match '(?i)(hit your|session|usage)\s+.*limit') {
            $retries = 0
            if ($job.PSObject.Properties['limitRetries'] -and $job.limitRetries) { $retries = [int]$job.limitRetries }
            if ($retries -ge 3) {
                Log "LIMIT-RETRY: session limit hit again but retry cap (3) reached; giving up and self-deleting."
            }
            else {
                # Parse "resets 9:40pm" style hints; fall back to now+3h if absent.
                $retryAt = (Get-Date).AddHours(3)
                if ($outText -match '(?i)resets\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)') {
                    $h = [int]$Matches[1]; $m = if ($Matches[2]) { [int]$Matches[2] } else { 0 }
                    if ($Matches[3] -ieq 'pm' -and $h -lt 12) { $h += 12 }
                    if ($Matches[3] -ieq 'am' -and $h -eq 12) { $h = 0 }
                    $candidate = (Get-Date).Date.AddHours($h).AddMinutes($m)
                    if ($candidate -le (Get-Date)) { $candidate = $candidate.AddDays(1) }
                    $retryAt = $candidate.AddMinutes(30)
                }
                try {
                    Set-ScheduledTask -TaskName $TaskName -TaskPath '\ClaudeOnce\' `
                        -Trigger (New-ScheduledTaskTrigger -Once -At $retryAt) -ErrorAction Stop | Out-Null
                    $job | Add-Member -NotePropertyName limitRetries -NotePropertyValue ($retries + 1) -Force
                    ($job | ConvertTo-Json) | Out-File -FilePath $jobFile -Encoding utf8
                    $selfDelete = $false
                    Log "LIMIT-RETRY: session limit hit; re-armed task for $($retryAt.ToString('yyyy-MM-dd HH:mm:ss')) (attempt $($retries + 1)/3)."
                }
                catch {
                    Log "LIMIT-RETRY: failed to re-arm trigger ($_); falling through to self-delete."
                }
            }
        }
    }
    elseif ($job.mode -eq 'shell') {
        # Run in THIS process via Invoke-Expression — forwarding to a child `powershell -Command`
        # mangles embedded quotes (Windows native-arg parsing strips them). The payload is
        # trusted (the user scheduled it). $LASTEXITCODE / $? reflect the command's result.
        Log "RUN  (in-process) <payload>"
        Invoke-Expression $job.payload *>&1 | Tee-Object -FilePath $logFile -Append
        Log "shell ok=$? exit=$LASTEXITCODE"
    }
    else {
        Log "ERROR: unknown mode '$($job.mode)'"
    }
}
catch {
    Log "EXCEPTION: $_"
}
finally {
    # Self-delete: this is a one-time task. Remove it and its job sidecar so nothing
    # lingers — unless a premature fire or a limit-retry re-arm asked us to keep it.
    if ($selfDelete) {
        try { Unregister-ScheduledTask -TaskName $TaskName -TaskPath '\ClaudeOnce\' -Confirm:$false -ErrorAction SilentlyContinue } catch {}
        try { Remove-Item -Path $jobFile -Force -ErrorAction SilentlyContinue } catch {}
    }
    # Orphan sweep (CLAUDE.md process hygiene): kill stray test-runner node procs this run may have spawned.
    try {
        Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -match 'vitest|turbo|tinypool' } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    } catch {}
    Log "END $TaskName"
}
