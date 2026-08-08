<#
.SYNOPSIS
  Claim one .claude/todos/ backlog item per ai-todos-format.md's Claims contract.

.DESCRIPTION
  Implements the documented protocol: write claim content to a private temp file,
  atomically rename it to .claims/<id>.claim with no-overwrite semantics, retry once
  after ~2s on a transient Windows filter-driver error before concluding anything, and
  treat an existing claim as stale (safe to steal) only when its mtime is older than 4
  hours AND the recorded pid is no longer alive on this machine.

  Duplicate-id-safe: if the id matches more than one backlog file (a known collision
  case in this project), -Slug picks one and the claim is named "<id>-<slug>.claim" so
  the sibling file's own claim is never touched.

.PARAMETER Id
  The numeric todo id (leading zeros optional). Also accepts a full filename stem
  (e.g. "434-real-slug") to disambiguate an id shared by two files without -Slug.

.PARAMETER Slug
  Optional disambiguator when the id matches more than one backlog file.

.PARAMETER RepoRoot
  Project root containing .claude/todos/. Defaults to the current directory.

.EXAMPLE
  ~/.claude/skills/close/claim-todo.ps1 -Id 286
  ~/.claude/skills/close/claim-todo.ps1 -Id 434 -Slug chat-row-style-decide-and-delete-loser
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Id,

    [string]$Slug,

    [string]$RepoRoot = (Get-Location).Path
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host $msg }
function Write-Fail($msg) { Write-Error $msg }

$todosDir  = Join-Path $RepoRoot '.claude\todos'
$claimsDir = Join-Path $todosDir '.claims'

if (-not (Test-Path $todosDir)) {
    Write-Fail "No .claude\todos found under '$RepoRoot' (looked for '$todosDir')."
}

# $Id may be a bare numeric id ("434") or a full stem ("434-real-slug") passed
# instead of -Slug; either way $numericId is what the claim file is keyed on.
if ($Id -match '^0*(\d+)-(.+)$') {
    $numericId = $matches[1]
    if (-not $Slug) { $Slug = $matches[2] }
}
else {
    $numericId = $Id
}

# --- Locate the todo being claimed (active backlog only - done/ is not claimable) ---

$idPattern = "^0*$([regex]::Escape($numericId))-.*\.md$"
$backlogMatches = Get-ChildItem -Path $todosDir -Filter '*.md' -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match $idPattern }

if ($backlogMatches.Count -eq 0) {
    Write-Fail "No active todo matching id '$Id' found in $todosDir."
}

$siblingCount = $backlogMatches.Count

# Apply the slug filter whenever one is known, not only when the id is
# currently ambiguous - otherwise a mismatched -Slug could silently claim
# the wrong file once a sibling collision is no longer present.
if ($backlogMatches.Count -gt 0 -and $Slug) {
    $slugPattern = "^0*$([regex]::Escape($numericId))-$([regex]::Escape($Slug))\.md$"
    $backlogMatches = $backlogMatches | Where-Object { $_.Name -match $slugPattern }
    if ($backlogMatches.Count -eq 0) {
        Write-Fail "No active todo matching id '$Id' with slug '$Slug' found in $todosDir."
    }
}

if ($backlogMatches.Count -gt 1) {
    Write-Fail "Ambiguous id '$Id': multiple files match in $todosDir - $($backlogMatches.Name -join ', '). Retry with -Slug <slug> or pass the full filename stem as -Id."
}

$todoFile = $backlogMatches[0]

# Slug-suffixed claim name only when the id actually collides, so the common
# case keeps the plain "<id>.claim" name existing consumers already expect.
$claimName = if ($siblingCount -gt 1) { "$numericId-$Slug.claim" } else { "$numericId.claim" }

if (-not (Test-Path $claimsDir)) {
    New-Item -ItemType Directory -Path $claimsDir -Force | Out-Null
}

$claimPath = Join-Path $claimsDir $claimName
$tempPath  = Join-Path $claimsDir "$claimName.tmp-$PID"

$sessionId = if ($env:CLAUDE_CODE_SESSION_ID) { $env:CLAUDE_CODE_SESSION_ID } else { "pid-$PID" }
$claimContent = @(
    "session: $sessionId"
    "pid: $PID"
    "started: $((Get-Date).ToUniversalTime().ToString('o'))"
) -join "`n"

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($tempPath, $claimContent, $utf8NoBom)

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

# Windows caveat: a sync/AV filter driver can throw a transient error that is
# NOT a lost race. Retry once after ~2s before concluding anything.
$claimed = Try-Rename -From $tempPath -To $claimPath
if (-not $claimed) {
    Start-Sleep -Seconds 2
    $claimed = Try-Rename -From $tempPath -To $claimPath
}

if ($claimed) {
    Write-Info "Claimed todo $numericId ($($todoFile.Name)) -> .claims\$claimName"
    exit 0
}

if (-not (Test-Path $claimPath)) {
    Remove-Item -Path $tempPath -Force -ErrorAction SilentlyContinue
    Write-Fail "Failed to claim todo ${numericId}: rename to '$claimPath' did not succeed and no existing claim blocks it."
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
    Write-Info "Todo $numericId already claimed (pid $existingPid, age $([math]::Round($ageHours, 2))h) - not stale, skipping."
    exit 1
}

Write-Info "Existing claim for $numericId is stale (age $([math]::Round($ageHours, 2))h, pid $existingPid not alive) - reclaiming."
Remove-Item -Path $claimPath -Force

if (Try-Rename -From $tempPath -To $claimPath) {
    Write-Info "Claimed todo $numericId ($($todoFile.Name)) -> .claims\$claimName"
    exit 0
}

Remove-Item -Path $tempPath -Force -ErrorAction SilentlyContinue
Write-Fail "Failed to reclaim stale claim for todo $numericId after clearing it."
