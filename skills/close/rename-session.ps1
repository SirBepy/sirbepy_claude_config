param(
    [Parameter(Mandatory=$true)]
    [string]$Name,
    [switch]$Close
)

# Resolve the current session's jsonl by:
# 1. Walking up the process tree from this script to find the claude.exe ancestor PID
# 2. Matching that PID against session JSON files in ~/.claude/sessions/
# 3. Globbing ~/.claude/projects/*/<sessionId>.jsonl to locate the actual transcript
#
# Then appending two JSONL records the harness recognizes as a session rename:
#   {"type":"custom-title","customTitle":"<name>","sessionId":"<id>"}
#   {"type":"agent-name","agentName":"<name>","sessionId":"<id>"}

$ErrorActionPreference = 'Stop'

$claudeRoot  = Join-Path $env:USERPROFILE '.claude'
$sessionsDir = Join-Path $claudeRoot 'sessions'
$projectsDir = Join-Path $claudeRoot 'projects'

if (-not (Test-Path $sessionsDir)) {
    Write-Error "Sessions dir not found: $sessionsDir"
    exit 1
}

# Walk up the process tree from $PID to find the claude.exe ancestor
function Get-AncestorClaudePid {
    $p = $PID
    for ($i = 0; $i -lt 8; $i++) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $p" -ErrorAction SilentlyContinue
        if (-not $proc) { break }
        if ($proc.Name -like '*claude*') { return [int]$p }
        $next = [int]$proc.ParentProcessId
        if ($next -eq 0 -or $next -eq $p) { break }
        $p = $next
    }
    return $null
}

$claudePid = Get-AncestorClaudePid

if (-not $claudePid) {
    Write-Error "Could not find a claude ancestor process from PID $PID"
    exit 1
}

$candidates = Get-ChildItem -Path $sessionsDir -Filter '*.json' -File -ErrorAction SilentlyContinue |
    ForEach-Object {
        try {
            $data = Get-Content -Raw -Path $_.FullName | ConvertFrom-Json
            if ($data.pid -and ([int]$data.pid -eq $claudePid)) {
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
    Write-Error "No session found with pid matching claude ancestor pid $claudePid"
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

Write-Host "Renamed session $sessionId (claude pid $claudePid) to '$Name'"
Write-Host "  jsonl: $jsonlPath"

if ($Close) {
    if (-not $claudePid) {
        Write-Warning "Close requested but no claude pid resolved. Skipping kill."
        exit 0
    }
    # Kill claude.exe directly. VS Code closes the terminal tab when its hosted process exits.
    $killCmd = "Start-Sleep -Milliseconds 800; try { Stop-Process -Id $claudePid -Force -ErrorAction Stop } catch {}"
    Start-Process -FilePath 'powershell.exe' `
        -ArgumentList '-NoProfile','-NonInteractive','-WindowStyle','Hidden','-Command',$killCmd `
        -WindowStyle Hidden | Out-Null
    Write-Host "Scheduled kill of claude pid $claudePid in 800ms."
}
