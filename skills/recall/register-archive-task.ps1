# Registers (or re-registers) the daily Windows scheduled task that runs `recall.py compress`.
# Safe to re-run: -Force replaces the existing task, e.g. after Python moves.
#
# Daily rather than monthly on purpose: the compressor is a no-op unless a month has become
# due, so the trigger cadence only bounds how late a due month gets archived, and PowerShell
# 5.1's New-ScheduledTaskTrigger has no -Monthly. StartWhenAvailable covers days the machine
# was off at the trigger time.

$ErrorActionPreference = 'Stop'
$taskName = 'Claude transcript archive'
$script = Join-Path $PSScriptRoot 'recall.py'

$python = (Get-Command python -ErrorAction Stop).Source
# pythonw.exe beside python.exe runs without flashing a console window at the trigger time.
$pythonw = Join-Path (Split-Path $python) 'pythonw.exe'
if (-not (Test-Path $pythonw)) { $pythonw = $python }

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$script`" compress"
$trigger = New-ScheduledTaskTrigger -Daily -At '12:30'
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 2)

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings `
    -Description 'Zips Claude Code transcripts older than last month into ~/.claude/memory-archive. See ~/.claude/refs/permanent-memory.md.' `
    -Force | Out-Null

# One immediate run writes the first compress.log line, which is what /recall's health check
# reads to tell "never set up" apart from "stopped running".
Start-ScheduledTask -TaskName $taskName
Write-Output "Registered '$taskName': daily 12:30, $pythonw `"$script`" compress"
