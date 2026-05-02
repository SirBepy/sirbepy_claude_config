param(
    [Parameter(Mandatory=$true)]
    [string]$Name,
    [switch]$Close
)

# Resolve the current session's jsonl by:
# 1. Scanning ~/.claude/sessions/*.json (process-state files written by the harness)
# 2. Matching the entry whose cwd == current $PWD (case-insensitive)
# 3. Picking the most recently updated match (handles stale exited sessions)
# 4. Globbing ~/.claude/projects/*/<sessionId>.jsonl to locate the actual transcript
#
# Then appending two JSONL records the harness recognizes as a session rename:
#   {"type":"custom-title","customTitle":"<name>","sessionId":"<id>"}
#   {"type":"agent-name","agentName":"<name>","sessionId":"<id>"}

$ErrorActionPreference = 'Stop'

$claudeRoot = Join-Path $env:USERPROFILE '.claude'
$sessionsDir = Join-Path $claudeRoot 'sessions'
$projectsDir = Join-Path $claudeRoot 'projects'
$cwd = (Get-Location).Path

if (-not (Test-Path $sessionsDir)) {
    Write-Error "Sessions dir not found: $sessionsDir"
    exit 1
}

$candidates = Get-ChildItem -Path $sessionsDir -Filter '*.json' -File -ErrorAction SilentlyContinue |
    ForEach-Object {
        try {
            $data = Get-Content -Raw -Path $_.FullName | ConvertFrom-Json
            if ($data.cwd -and ($data.cwd.TrimEnd('\','/') -ieq $cwd.TrimEnd('\','/'))) {
                [pscustomobject]@{
                    SessionId = $data.sessionId
                    Pid       = $data.pid
                    UpdatedAt = $data.updatedAt
                    Status    = $data.status
                    File      = $_.FullName
                }
            }
        } catch {}
    } | Sort-Object -Property UpdatedAt -Descending

if (-not $candidates -or $candidates.Count -eq 0) {
    Write-Error "No session found with cwd matching '$cwd'"
    exit 1
}

$sessionId   = $candidates[0].SessionId
$sessionPid  = $candidates[0].Pid
$jsonlMatches = Get-ChildItem -Path $projectsDir -Recurse -Filter "$sessionId.jsonl" -File -ErrorAction SilentlyContinue

if (-not $jsonlMatches -or $jsonlMatches.Count -eq 0) {
    Write-Error "Session jsonl not found for sessionId '$sessionId' under $projectsDir"
    exit 1
}

$jsonlPath = $jsonlMatches[0].FullName

$titleRecord = @{ type = 'custom-title'; customTitle = $Name; sessionId = $sessionId } | ConvertTo-Json -Compress
$agentRecord = @{ type = 'agent-name';   agentName   = $Name; sessionId = $sessionId } | ConvertTo-Json -Compress

Add-Content -Path $jsonlPath -Value $titleRecord -Encoding utf8
Add-Content -Path $jsonlPath -Value $agentRecord -Encoding utf8

Write-Host "Renamed session $sessionId to '$Name'"
Write-Host "  jsonl: $jsonlPath"

if ($Close) {
    if (-not $sessionPid) {
        Write-Warning "Close requested but no pid resolved for session $sessionId. Skipping kill."
        exit 0
    }
    # Spawn detached PowerShell that waits, then kills the claude process by pid.
    # Detached so the kill survives this script (and its parent claude.exe) exiting.
    $killCmd = "Start-Sleep -Milliseconds 800; try { Stop-Process -Id $sessionPid -Force -ErrorAction Stop } catch {}"
    Start-Process -FilePath 'powershell.exe' `
        -ArgumentList '-NoProfile','-NonInteractive','-WindowStyle','Hidden','-Command',$killCmd `
        -WindowStyle Hidden | Out-Null
    Write-Host "Scheduled kill of pid $sessionPid in 800ms."
}
