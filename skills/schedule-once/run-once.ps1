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

try {
    if (-not (Test-Path $jobFile)) { Log "ERROR: job file not found: $jobFile"; return }
    $job = Get-Content -Raw -Path $jobFile | ConvertFrom-Json

    Log "START $TaskName  mode=$($job.mode)  workDir=$($job.workDir)"
    if ($job.workDir -and (Test-Path $job.workDir)) { Set-Location -Path $job.workDir }

    if ($job.mode -eq 'prompt') {
        $exe = $job.claudeExe
        if (-not $exe -or -not (Test-Path $exe)) { $exe = (Get-Command claude -ErrorAction SilentlyContinue).Source }
        if (-not $exe) { Log "ERROR: claude executable not found"; return }
        Log "RUN  <prompt via stdin> | claude -p --permission-mode $($job.permMode)"
        # Pipe the prompt via stdin rather than as an arg — a native-arg prompt mangles
        # embedded quotes. -p reads stdin as the prompt (see `claude --help`: "useful for pipes").
        $job.payload | & $exe -p --permission-mode $job.permMode --no-session-persistence *>&1 |
            Tee-Object -FilePath $logFile -Append
        Log "claude exit code: $LASTEXITCODE"
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
    # Self-delete: this is a one-time task. Remove it and its job sidecar so nothing lingers.
    try { Unregister-ScheduledTask -TaskName $TaskName -TaskPath '\ClaudeOnce\' -Confirm:$false -ErrorAction SilentlyContinue } catch {}
    try { Remove-Item -Path $jobFile -Force -ErrorAction SilentlyContinue } catch {}
    # Orphan sweep (CLAUDE.md process hygiene): kill stray test-runner node procs this run may have spawned.
    try {
        Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -match 'vitest|turbo|tinypool' } |
            ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    } catch {}
    Log "END $TaskName"
}
