<#
.SYNOPSIS
  Claim one or more .claude/todos/ backlog items per ai-todos-format.md's Claims contract.

.DESCRIPTION
  Implements the documented protocol: write claim content to a private temp file,
  atomically rename it to .claims/<id>.claim (<id> = the canonical device-prefixed form,
  e.g. pc-1407.claim) with no-overwrite semantics, retry once after ~2s on a transient
  Windows filter-driver error before concluding anything, and treat an existing claim as
  stale (safe to steal) only when its mtime is older than 4 hours AND the recorded pid is
  no longer alive on this machine.

  Id resolution lives in _shared.ps1's Resolve-TodoFile: a full id (pc-1407, any padding)
  is used as-is; a bare number (1407) resolves to THIS device's label first, else a unique
  match on another label, else an error naming the candidates; a legacy bare-numeric
  filename reads as label pc.

  Batch form: -Id accepts a comma-separated list, either as separate PowerShell
  arguments (-Id pc-0003,pc-0004) or as one quoted string (-Id "03,04,05") - both bind
  and claim every one of them in this single call. Handling N todos together this way
  costs one remembered claim call, the same as handling one - see close/ai-todos-format.md's
  Claims section for the incident (todo 484) this closes: a claim call that has to be
  remembered once per todo gets skipped exactly when several todos move at once.

  A bare unquoted number list is NOT equivalent to the quoted form: PowerShell parses an
  unquoted comma list of digits as numeric literals before this script ever runs, so
  -Id 08,20 arrives here as "8","20" with the padding already gone (todo 1024). Padding is
  irrelevant to the claim name (it is always the canonical 4-digit form), but the quoted
  form (-Id "08,20") still preserves the id exactly as typed, and a full device-prefixed id
  (pc-0008) sidesteps the issue entirely. Prefer one of those.

  Duplicate-id-safe: if an id matches more than one backlog file (a known collision
  case in this project), -Slug picks one and the claim is named "<id>-<slug>.claim" so
  the sibling file's own claim is never touched. In a batch, embed the slug inline as
  the full filename stem instead of using -Slug (which only disambiguates a single id).

.PARAMETER Id
  A todo id (pc-1407, or a bare number 1407; leading zeros optional), a full filename stem
  to disambiguate an id shared by two files (e.g. "pc-0434-real-slug"), or a
  comma-separated list of either for a batch claim - as separate arguments or one quoted
  string ("03,04,05" or "03,pc-0434-real-slug,05"), both work.

.PARAMETER Slug
  Optional disambiguator when a single id matches more than one backlog file. Not valid
  together with a multi-id batch - use the full stem form per id instead.

.PARAMETER RepoRoot
  Project root containing .claude/todos/. Defaults to the current directory.

.EXAMPLE
  ~/.claude/skills/close/claim-todo.ps1 -Id pc-0286
  ~/.claude/skills/close/claim-todo.ps1 -Id 286
  ~/.claude/skills/close/claim-todo.ps1 -Id pc-0434 -Slug chat-row-style-decide-and-delete-loser
  ~/.claude/skills/close/claim-todo.ps1 -Id "pc-0003,pc-0004,pc-0005"
#>
param(
    [Parameter(Mandatory = $true)]
    [string[]]$Id,

    [string]$Slug,

    [string]$RepoRoot = (Get-Location).Path
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot '_shared.ps1')

function Write-Info($msg) { Write-Host $msg }

$todosDir  = Join-Path $RepoRoot '.claude\todos'
$claimsDir = Join-Path $todosDir '.claims'

if (-not (Test-Path $todosDir)) {
    Write-Host "ERROR: No .claude\todos found under '$RepoRoot' (looked for '$todosDir')." -ForegroundColor Red
    exit 2
}

# PowerShell itself - not this script - parses an UNQUOTED comma list like
# "-Id 08,20" as an array of numeric literals before this param block ever runs,
# which drops any leading zero (08 becomes 8) with no way for this script to recover
# it after the fact (confirmed root cause, todo 1024). $Id arrives already split into
# more than one element ONLY through that path: a single quoted string always binds
# as a 1-element array here, so Count -gt 1 at this point is the tell.
if ($Id.Count -gt 1) {
    Write-Host "NOTE: -Id arrived pre-split into $($Id.Count) separate values, which means PowerShell already parsed this batch as numbers before this script started - any zero-padding (e.g. 08) is already gone and cannot be recovered here. If padding matters, re-run with the whole list quoted: -Id `"$($Id -join ',')`"." -ForegroundColor Yellow
}

# -Id is [string[]] so both unquoted array args (-Id 03,04,05) and one quoted
# comma-string (-Id "03,04,05") bind; re-join then split covers both shapes.
$rawIds = ($Id -join ',') -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }
if ($rawIds.Count -eq 0) {
    Write-Host "ERROR: -Id resolved to no ids." -ForegroundColor Red
    exit 2
}
if ($rawIds.Count -gt 1 -and $Slug) {
    Write-Host "ERROR: -Slug applies to a single id only. For a batch with a colliding id, pass its full filename stem inline instead (e.g. -Id `"pc-0003,pc-0434-real-slug,pc-0005`")." -ForegroundColor Red
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

# Stale = mtime > 4h AND the recorded pid is no longer THIS identity. Returns the numbers
# the callers' messages need alongside the verdict.
function Get-ClaimStaleness {
    param([string]$ClaimFile)

    $existing = Get-Item -Path $ClaimFile
    $existingPid = $null
    $existingStartTicks = $null
    $existingContent = Get-Content -Path $ClaimFile -Raw -ErrorAction SilentlyContinue
    if ($existingContent -match 'pid:\s*(\d+)') {
        $existingPid = [int]$matches[1]
    }
    if ($existingContent -match 'procStartTicks:\s*(\d+)') {
        $existingStartTicks = [int64]$matches[1]
    }

    # A bare pid is not a reliable liveness signal: Windows recycles pids, so an
    # unrelated later process can inherit the number and keep a dead session's
    # claim alive forever (same recycled-pid failure the reservation markers hit).
    # When the claim carries procStartTicks, liveness requires the pid to be
    # running AND its own start time to match what was recorded. A claim written
    # before this field existed has no start time to confirm against, so it
    # falls back to the old pid-only check.
    $hasStartSignal = [bool]$existingStartTicks
    $pidAlive = $false
    if ($existingPid -and $hasStartSignal) {
        $proc = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
        if ($proc) { $pidAlive = ($proc.StartTime.Ticks -eq $existingStartTicks) }
    }
    elseif ($existingPid) {
        $pidAlive = [bool](Get-Process -Id $existingPid -ErrorAction SilentlyContinue)
    }

    $ageHours = ((Get-Date) - $existing.LastWriteTime).TotalHours
    return [pscustomobject]@{
        IsStale  = (($ageHours -gt 4) -and (-not $pidAlive))
        Pid      = $existingPid
        AgeHours = $ageHours
    }
}

# Claims one id; returns a result record instead of exiting, so a batch keeps going
# past one bad id rather than aborting the whole call.
function Claim-One {
    param([string]$RawId, [string]$SlugParam)

    $resolved = Resolve-TodoFile -Dir $todosDir -RawId $RawId -Slug $SlugParam
    $todoId = $resolved.Id
    $slugLocal = $resolved.Slug
    $backlogMatches = @($resolved.Matches)

    if ($resolved.Error) {
        return [ordered]@{ Id = $todoId; Reason = 'error'; Message = $resolved.Error }
    }

    if ($resolved.FellBack) {
        Write-Info "WARNING: todo '$RawId' has no device-prefixed id, which ai-todos-format.md treats as malformed. Claiming it anyway; rename it via reserve-todo-id.ps1 so it can be referenced by id."
    }

    if ($backlogMatches.Count -eq 0) {
        if ($resolved.SiblingCount -gt 0 -and $slugLocal) {
            return [ordered]@{ Id = $todoId; Reason = 'error'; Message = "No active todo matching id '$RawId' with slug '$slugLocal' found in $todosDir." }
        }
        return [ordered]@{ Id = $todoId; Reason = 'error'; Message = "No active todo matching id '$RawId' found in $todosDir." }
    }

    if ($backlogMatches.Count -gt 1) {
        return [ordered]@{ Id = $todoId; Reason = 'error'; Message = "Ambiguous id '$RawId': multiple files match in $todosDir - $($backlogMatches.Name -join ', '). Retry with -Slug <slug> or pass the full filename stem as -Id." }
    }

    $todoFile = $backlogMatches[0]
    $claimName = if ($resolved.SiblingCount -gt 1) { "$todoId-$slugLocal.claim" } else { "$todoId.claim" }

    # A claim a live session holds under an older name (a bare "1407.claim" from before
    # device-prefixed ids) guards the same todo; leaving it be would let a second session
    # claim it again under the canonical name.
    if ($resolved.Label) {
        $claimSlug = $null
        if ($resolved.SiblingCount -gt 1) { $claimSlug = $slugLocal }
        $olderNamed = @(Find-TodoClaims -ClaimsDir $claimsDir -Label $resolved.Label -Number $resolved.Number -Slug $claimSlug |
            Where-Object { $_.Name -ne $claimName })
        foreach ($old in $olderNamed) {
            $oldState = Get-ClaimStaleness -ClaimFile $old.FullName
            if (-not $oldState.IsStale) {
                return [ordered]@{ Id = $todoId; Reason = 'conflict'; Message = "Todo $todoId already claimed under the older name $($old.Name) (pid $($oldState.Pid), age $([math]::Round($oldState.AgeHours, 2))h) - not stale, skipping." }
            }
            Remove-Item -Path $old.FullName -Force
        }
    }

    $claimPath = Join-Path $claimsDir $claimName
    $tempPath  = Join-Path $claimsDir "$claimName.tmp-$PID"

    $sessionId = if ($env:CLAUDE_CODE_SESSION_ID) { $env:CLAUDE_CODE_SESSION_ID } else { "pid-$PID" }
    # procStartTicks disambiguates this pid from a later, unrelated process that
    # inherits the same number after Windows recycles it - same <pid>-<start-ticks>
    # identity reserve-todo-id.ps1 adopted for reservation markers (todo 988).
    $procStartTicks = (Get-Process -Id $PID).StartTime.Ticks
    $claimContent = @(
        "session: $sessionId"
        "pid: $PID"
        "procStartTicks: $procStartTicks"
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
        return [ordered]@{ Id = $todoId; Reason = 'claimed'; Message = "Claimed todo $todoId ($($todoFile.Name)) -> .claims\$claimName" }
    }

    if (-not (Test-Path $claimPath)) {
        Remove-Item -Path $tempPath -Force -ErrorAction SilentlyContinue
        return [ordered]@{ Id = $todoId; Reason = 'error'; Message = "Failed to claim todo ${todoId}: rename to '$claimPath' did not succeed and no existing claim blocks it." }
    }

    # Destination exists - a real conflict.
    $state = Get-ClaimStaleness -ClaimFile $claimPath
    if (-not $state.IsStale) {
        Remove-Item -Path $tempPath -Force -ErrorAction SilentlyContinue
        return [ordered]@{ Id = $todoId; Reason = 'conflict'; Message = "Todo $todoId already claimed (pid $($state.Pid), age $([math]::Round($state.AgeHours, 2))h) - not stale, skipping." }
    }

    Remove-Item -Path $claimPath -Force
    if (Try-Rename -From $tempPath -To $claimPath) {
        return [ordered]@{ Id = $todoId; Reason = 'claimed'; Message = "Existing claim for $todoId was stale (age $([math]::Round($state.AgeHours, 2))h, pid $($state.Pid) not alive or recycled) - reclaimed ($($todoFile.Name)) -> .claims\$claimName" }
    }

    Remove-Item -Path $tempPath -Force -ErrorAction SilentlyContinue
    return [ordered]@{ Id = $todoId; Reason = 'error'; Message = "Failed to reclaim stale claim for todo $todoId after clearing it." }
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
