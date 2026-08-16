param(
    [Parameter(Mandatory=$false)]
    [string]$Name = "",
    [switch]$Close,
    [switch]$GetId
)

# Resolve the current session by matching $env:CLAUDE_CODE_SESSION_ID against
# ~/.claude/sessions/*.json - stable per session, unlike a process-tree walk (todo 60: the walk
# returned two different PIDs at two different points in the SAME session). Falls back to the
# old walk only when the env var is unset (older harness / plain terminal).
#
# -GetId prints "<pid>-<procStart-ticks>" for the current session and exits - the canonical
# screenshot-subfolder id other skills (/close Phase 0, /screenshot, /mockup) should call instead
# of hand-rolling their own walk.

$ErrorActionPreference = 'Stop'

$claudeRoot  = Join-Path $env:USERPROFILE '.claude'
$sessionsDir = Join-Path $claudeRoot 'sessions'
$projectsDir = Join-Path $claudeRoot 'projects'

if (-not (Test-Path $sessionsDir)) {
    Write-Error "Sessions dir not found: $sessionsDir"
    exit 1
}

# Fallback only, best-effort/unstable (todo 60) - used when CLAUDE_CODE_SESSION_ID is unset.
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

# Resolves this session's own record from sessions/*.json. sessionId match is authoritative;
# the pid-walk match only runs when the env var is unset. Tags via _resolvedVia (todo 346).
function Resolve-SessionRecord {
    $sid = $env:CLAUDE_CODE_SESSION_ID
    if ($sid) {
        $match = Get-ChildItem -Path $sessionsDir -Filter '*.json' -File -ErrorAction SilentlyContinue |
            ForEach-Object {
                try {
                    $d = Get-Content -Raw -Path $_.FullName | ConvertFrom-Json
                    if ($d.sessionId -eq $sid) { $d }
                } catch {}
            } | Select-Object -First 1
        if ($match) {
            $match | Add-Member -NotePropertyName _resolvedVia -NotePropertyValue 'sessionId' -Force
            return $match
        }
    }

    $claudePid = Get-AncestorClaudePid
    if (-not $claudePid) { return $null }

    $fallback = Get-ChildItem -Path $sessionsDir -Filter '*.json' -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            try {
                $d = Get-Content -Raw -Path $_.FullName | ConvertFrom-Json
                if ($d.pid -and ([int]$d.pid -eq $claudePid)) { $d }
            } catch {}
        } | Sort-Object -Property UpdatedAt -Descending | Select-Object -First 1
    if ($fallback) {
        $fallback | Add-Member -NotePropertyName _resolvedVia -NotePropertyValue 'pidwalk' -Force
    }
    return $fallback
}

if ($GetId) {
    $record = Resolve-SessionRecord
    if (-not $record) {
        Write-Error "Could not resolve this session's own record (sessionId env var unset and pid-walk fallback failed)."
        exit 1
    }
    if ($record._resolvedVia -eq 'pidwalk') {
        # sessionId lookup missed; only the unstable pid-walk (todo 60) matched (todo 346).
        Write-Error "Refusing -GetId: sessionId lookup failed, only the unreliable process-tree fallback matched. Per refs/delegation-doctrine.md, the orchestrator resolves this id ONCE and passes it into every dispatch - never re-derive it here."
        exit 1
    }
    $ticks = $record.procStart
    if (-not $ticks) {
        # Older session json with no procStart - derive it from the already-known pid, no walk needed.
        $ticks = (Get-Process -Id ([int]$record.pid)).StartTime.Ticks
    }
    Write-Output "$($record.pid)-$ticks"
    exit 0
}

if ($Name) {
    $record = Resolve-SessionRecord
    if (-not $record) {
        Write-Error "Could not resolve this session's own record to rename."
        exit 1
    }

    $sessionId = $record.sessionId
    $jsonlMatches = Get-ChildItem -Path $projectsDir -Recurse -Filter "$sessionId.jsonl" -File -ErrorAction SilentlyContinue

    if (-not $jsonlMatches -or $jsonlMatches.Count -eq 0) {
        Write-Error "Session jsonl not found for sessionId '$sessionId' under $projectsDir"
        exit 1
    }

    $jsonlPath = $jsonlMatches[0].FullName

    $titleRecord = @{ type = 'custom-title'; customTitle = $Name; sessionId = $sessionId } | ConvertTo-Json -Compress
    $agentRecord = @{ type = 'agent-name';   agentName   = $Name; sessionId = $sessionId } | ConvertTo-Json -Compress

    $maxAttempts = 8
    $retryMs     = 250

    foreach ($line in @($titleRecord, $agentRecord)) {
        $written = $false
        for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
            try {
                Add-Content -Path $jsonlPath -Value $line -Encoding utf8
                $written = $true
                break
            } catch {
                if ($attempt -lt $maxAttempts) {
                    Start-Sleep -Milliseconds $retryMs
                } else {
                    Write-Error "Could not write record to jsonl after $maxAttempts attempts: $_"
                    exit 1
                }
            }
        }
    }

    Write-Host "Renamed session $sessionId (pid $($record.pid)) to '$Name'"
    Write-Host "  jsonl: $jsonlPath"
}

if ($Close) {
    $record = Resolve-SessionRecord
    if (-not $record) {
        Write-Warning "Close requested but session record could not be resolved. Skipping kill."
        exit 0
    }
    $claudePid = [int]$record.pid
    # Kill claude.exe directly. VS Code closes the terminal tab when its hosted process exits.
    $killCmd = "Start-Sleep -Milliseconds 800; try { Stop-Process -Id $claudePid -Force -ErrorAction Stop } catch {}"
    Start-Process -FilePath 'powershell.exe' `
        -ArgumentList '-NoProfile','-NonInteractive','-WindowStyle','Hidden','-Command',$killCmd `
        -WindowStyle Hidden | Out-Null
    Write-Host "Scheduled kill of claude pid $claudePid in 800ms."
}
