<#
.SYNOPSIS
  Claim one or more .claude/todos/ backlog items per ai-todos-format.md's Claims contract.

.DESCRIPTION
  Implements the documented protocol: write claim content to a private temp file,
  atomically rename it to .claims/<id>.claim with no-overwrite semantics, retry once
  after ~2s on a transient Windows filter-driver error before concluding anything, and
  treat an existing claim as stale (safe to steal) only when its mtime is older than 4
  hours AND the recorded pid is no longer alive on this machine.

  Batch form: -Id accepts a comma-separated list ("03,04,05") and claims every one of
  them in this single call. Handling N todos together this way costs one remembered
  claim call, the same as handling one - see close/ai-todos-format.md's Claims section
  for the incident (todo 484) this closes: a claim call that has to be remembered once
  per todo gets skipped exactly when several todos move at once.

  Duplicate-id-safe: if an id matches more than one backlog file (a known collision
  case in this project), -Slug picks one and the claim is named "<id>-<slug>.claim" so
  the sibling file's own claim is never touched. In a batch, embed the slug inline as
  the full filename stem instead of using -Slug (which only disambiguates a single id).

.PARAMETER Id
  A numeric todo id (leading zeros optional), a full filename stem to disambiguate an id
  shared by two files (e.g. "434-real-slug"), or a comma-separated list of either for a
  batch claim ("03,04,05" or "03,434-real-slug,05").

.PARAMETER Slug
  Optional disambiguator when a single id matches more than one backlog file. Not valid
  together with a multi-id batch - use the full stem form per id instead.

.PARAMETER RepoRoot
  Project root containing .claude/todos/. Defaults to the current directory.

.EXAMPLE
  ~/.claude/skills/close/claim-todo.ps1 -Id 286
  ~/.claude/skills/close/claim-todo.ps1 -Id 434 -Slug chat-row-style-decide-and-delete-loser
  ~/.claude/skills/close/claim-todo.ps1 -Id 03,04,05
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Id,

    [string]$Slug,

    [string]$RepoRoot = (Get-Location).Path
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host $msg }

$todosDir  = Join-Path $RepoRoot '.claude\todos'
$claimsDir = Join-Path $todosDir '.claims'

if (-not (Test-Path $todosDir)) {
    Write-Host "ERROR: No .claude\todos found under '$RepoRoot' (looked for '$todosDir')." -ForegroundColor Red
    exit 2
}

$rawIds = $Id -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
if ($rawIds.Count -eq 0) {
    Write-Host "ERROR: -Id resolved to no ids." -ForegroundColor Red
    exit 2
}
if ($rawIds.Count -gt 1 -and $Slug) {
    Write-Host "ERROR: -Slug applies to a single id only. For a batch with a colliding id, pass its full filename stem inline instead (e.g. -Id 03,434-real-slug,05)." -ForegroundColor Red
    exit 2
}

if (-not (Test-Path $claimsDir)) {
    New-Item -ItemType Directory -Path $claimsDir -Force | Out-Null
}

function Try-Rename {
    param([string]$From, [string]$To)
    try {
        Move-Item -Path $From -Destination $To -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

# Claims one id; returns a result record instead of exiting, so a batch keeps going
# past one bad id rather than aborting the whole call.
function Claim-One {
    param([string]$RawId, [string]$SlugParam)

    $numericId = $RawId
    $slugLocal = $SlugParam
    if ($RawId -match '^0*(\d+)-(.+)$') {
        $numericId = $matches[1]
        if (-not $slugLocal) { $slugLocal = $matches[2] }
    }

    $idPattern = "^0*$([regex]::Escape($numericId))-.*\.md$"
    $allBacklog = Get-ChildItem -Path $todosDir -Filter '*.md' -File -ErrorAction SilentlyContinue
    $backlogMatches = $allBacklog | Where-Object { $_.Name -match $idPattern }

    if ($backlogMatches.Count -eq 0 -and $numericId -notmatch '^\d+$') {
        $stemPattern = "^$([regex]::Escape($numericId))\.md$"
        $backlogMatches = $allBacklog | Where-Object { $_.Name -match $stemPattern }
        if ($backlogMatches.Count -gt 0) {
            Write-Info "WARNING: todo '$RawId' has no numeric prefix, which ai-todos-format.md treats as malformed. Claiming it anyway; rename it via reserve-todo-id.ps1 so it can be referenced by id."
            $slugLocal = $null
        }
    }

    if ($backlogMatches.Count -eq 0) {
        return [ordered]@{ Id = $numericId; Reason = 'error'; Message = "No active todo matching id '$RawId' found in $todosDir." }
    }

    $siblingCount = $backlogMatches.Count

    if ($backlogMatches.Count -gt 0 -and $slugLocal) {
        $slugPattern = "^0*$([regex]::Escape($numericId))-$([regex]::Escape($slugLocal))\.md$"
        $backlogMatches = $backlogMatches | Where-Object { $_.Name -match $slugPattern }
        if ($backlogMatches.Count -eq 0) {
            return [ordered]@{ Id = $numericId; Reason = 'error'; Message = "No active todo matching id '$RawId' with slug '$slugLocal' found in $todosDir." }
        }
    }

    if ($backlogMatches.Count -gt 1) {
        return [ordered]@{ Id = $numericId; Reason = 'error'; Message = "Ambiguous id '$RawId': multiple files match in $todosDir - $($backlogMatches.Name -join ', '). Retry with -Slug <slug> or pass the full filename stem as -Id." }
    }

    $todoFile = $backlogMatches[0]
    $claimName = if ($siblingCount -gt 1) { "$numericId-$slugLocal.claim" } else { "$numericId.claim" }

    $claimPath = Join-Path $claimsDir $claimName
    $tempPath  = Join-Path $claimsDir "$claimName.tmp-$PID"

    $sessionId = if ($env:CLAUDE_CODE_SESSION_ID) { $env:CLAUDE_CODE_SESSION_ID } else { "pid-$PID" }
    $claimContent = @(
        "session: $sessionId"
        "pid: $PID"
        "started: $((Get-Date).ToUniversalTime().ToString('o'))"
    ) -join "`r`n"
    $claimContent += "`r`n"

    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($tempPath, $claimContent, $utf8NoBom)

    # Windows caveat: a sync/AV filter driver can throw a transient error that is
    # NOT a lost race. Retry once after ~2s before concluding anything.
    $claimed = Try-Rename -From $tempPath -To $claimPath
    if (-not $claimed) {
        Start-Sleep -Seconds 2
        $claimed = Try-Rename -From $tempPath -To $claimPath
    }

    if ($claimed) {
        return [ordered]@{ Id = $numericId; Reason = 'claimed'; Message = "Claimed todo $numericId ($($todoFile.Name)) -> .claims\$claimName" }
    }

    if (-not (Test-Path $claimPath)) {
        Remove-Item -Path $tempPath -Force -ErrorAction SilentlyContinue
        return [ordered]@{ Id = $numericId; Reason = 'error'; Message = "Failed to claim todo ${numericId}: rename to '$claimPath' did not succeed and no existing claim blocks it." }
    }

    # Destination exists - a real conflict. Stale = mtime > 4h AND recorded pid is dead.
    $existing = Get-Item -Path $claimPath
    $existingPid = $null
    $existingContent = Get-Content -Path $claimPath -Raw -ErrorAction SilentlyContinue
    if ($existingContent -match 'pid:\s*(\d+)') {
        $existingPid = [int]$matches[1]
    }

    $pidAlive = $false
    if ($existingPid) {
        $pidAlive = [bool](Get-Process -Id $existingPid -ErrorAction SilentlyContinue)
    }

    $ageHours = ((Get-Date) - $existing.LastWriteTime).TotalHours
    $isStale = ($ageHours -gt 4) -and (-not $pidAlive)

    if (-not $isStale) {
        Remove-Item -Path $tempPath -Force -ErrorAction SilentlyContinue
        return [ordered]@{ Id = $numericId; Reason = 'conflict'; Message = "Todo $numericId already claimed (pid $existingPid, age $([math]::Round($ageHours, 2))h) - not stale, skipping." }
    }

    Remove-Item -Path $claimPath -Force
    if (Try-Rename -From $tempPath -To $claimPath) {
        return [ordered]@{ Id = $numericId; Reason = 'claimed'; Message = "Existing claim for $numericId was stale (age $([math]::Round($ageHours, 2))h, pid $existingPid not alive) - reclaimed ($($todoFile.Name)) -> .claims\$claimName" }
    }

    Remove-Item -Path $tempPath -Force -ErrorAction SilentlyContinue
    return [ordered]@{ Id = $numericId; Reason = 'error'; Message = "Failed to reclaim stale claim for todo $numericId after clearing it." }
}

$results = @()
foreach ($rawId in $rawIds) {
    $results += [pscustomobject](Claim-One -RawId $rawId -SlugParam $Slug)
}

foreach ($r in $results) {
    Write-Info $r.Message
}

if ($results | Where-Object { $_.Reason -eq 'error' }) { exit 2 }
if ($results | Where-Object { $_.Reason -eq 'conflict' }) { exit 1 }
exit 0
