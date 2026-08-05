<#
.SYNOPSIS
  Completion bookkeeping for one .claude/todos/ backlog item.

.DESCRIPTION
  Per ai-todos-format.md's "Release" contract, completing a todo means:
    1. Move .claude/todos/<id>-*.md to .claude/todos/done/ (creating done/ if missing).
    2. Delete .claude/todos/.claims/<id>.claim if present.
    3. Prune any "- [ ] <id> ..." line from .claude/todos/PLAN.md, re-reading the file
       fresh immediately before the write (CAS discipline - PLAN.md may be hand-edited
       or touched by another session between read and write).

  Idempotent: re-running against an already-completed id reports clearly and makes no
  further changes, rather than erroring or double-acting.

.PARAMETER Id
  The numeric todo id (leading zeros optional - "07" and "7" both match a file named
  "07-fix-auth-redirect.md"). Also accepts a full filename stem (e.g. "434-real-slug")
  to disambiguate an id shared by two files without needing -Slug.

.PARAMETER Slug
  Optional disambiguator when the id matches more than one backlog file (a known
  collision case in this project). Combined with Id to pick one file unambiguously.

.PARAMETER RepoRoot
  Project root containing .claude/todos/. Defaults to the current directory.

.EXAMPLE
  ~/.claude/skills/close/complete-todo.ps1 -Id 286
  ~/.claude/skills/close/complete-todo.ps1 -Id 07 -RepoRoot C:\Users\joe\Projects\my-app
  ~/.claude/skills/close/complete-todo.ps1 -Id 434 -Slug chat-row-style-decide-and-delete-loser
  ~/.claude/skills/close/complete-todo.ps1 -Id 434-chat-row-style-decide-and-delete-loser
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
$doneDir   = Join-Path $todosDir 'done'
$claimsDir = Join-Path $todosDir '.claims'
$planPath  = Join-Path $todosDir 'PLAN.md'

if (-not (Test-Path $todosDir)) {
    Write-Fail "No .claude\todos found under '$RepoRoot' (looked for '$todosDir')."
}

# $Id may be a bare numeric id ("434") or a full stem ("434-real-slug") passed
# instead of -Slug; either way $numericId is what claim/PLAN lookups key on.
if ($Id -match '^0*(\d+)-(.+)$') {
    $numericId = $matches[1]
    if (-not $Slug) { $Slug = $matches[2] }
}
else {
    $numericId = $Id
}

$idPattern = "^0*$([regex]::Escape($numericId))-.*\.md$"
$slugPattern = $null
if ($Slug) { $slugPattern = "^0*$([regex]::Escape($numericId))-$([regex]::Escape($Slug))\.md$" }

# --- Step 1: move the backlog file to done/ (or detect it's already there) ---

$backlogMatches = Get-ChildItem -Path $todosDir -Filter '*.md' -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match $idPattern }

# Apply the slug filter whenever one is known - not only when the id is
# currently ambiguous, or a stale/mismatched -Slug could silently resolve to
# the WRONG file once a sibling collision is no longer present.
if ($backlogMatches -and $Slug) {
    $backlogMatches = $backlogMatches | Where-Object { $_.Name -match $slugPattern }
}

if ($backlogMatches -and $backlogMatches.Count -gt 1) {
    Write-Fail "Ambiguous id '$Id': multiple files match in $todosDir - $($backlogMatches.Name -join ', '). Retry with -Slug <slug> or pass the full filename stem as -Id."
}

if ($backlogMatches -and $backlogMatches.Count -eq 1) {
    $todoFile = $backlogMatches[0]

    if (-not (Test-Path $doneDir)) {
        New-Item -ItemType Directory -Path $doneDir -Force | Out-Null
    }

    $destPath = Join-Path $doneDir $todoFile.Name
    if (Test-Path $destPath) {
        Write-Fail "Refusing to overwrite: '$destPath' already exists in done/."
    }

    Move-Item -Path $todoFile.FullName -Destination $destPath
    Write-Info "Moved $($todoFile.Name) -> done\$($todoFile.Name)"
}
else {
    # Not in the active backlog - check whether it's already been completed.
    $doneMatches = @()
    if (Test-Path $doneDir) {
        $doneMatches = Get-ChildItem -Path $doneDir -Filter '*.md' -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match $idPattern }
    }

    if ($doneMatches.Count -gt 0 -and $Slug) {
        $doneMatches = $doneMatches | Where-Object { $_.Name -match $slugPattern }
    }

    if ($doneMatches.Count -gt 1) {
        Write-Fail "Ambiguous id '$Id' in done\: $($doneMatches.Name -join ', '). Retry with -Slug <slug> or pass the full filename stem as -Id."
    }
    elseif ($doneMatches.Count -eq 1) {
        Write-Info "Todo $numericId already completed (found in done\$($doneMatches[0].Name)) - skipping move."
    }
    else {
        Write-Fail "No todo file matching id '$Id' found in $todosDir or $doneDir."
    }
}

# --- Step 2: release the claim, if any ---
# Claim files are normally "<id>.claim", but claim-todo.ps1 names them
# "<id>-<slug>.claim" when the id collides, so a sibling task's claim survives.

$claimMatches = @()
if (Test-Path $claimsDir) {
    if ($Slug) {
        $claimMatches = Get-ChildItem -Path $claimsDir -Filter '*.claim' -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match "^0*$([regex]::Escape($numericId))-$([regex]::Escape($Slug))\.claim$" }
    }
    if ($claimMatches.Count -eq 0) {
        $claimMatches = Get-ChildItem -Path $claimsDir -Filter '*.claim' -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match "^0*$([regex]::Escape($numericId))\.claim$" }
    }
    if ($claimMatches.Count -eq 0) {
        $wildcard = Get-ChildItem -Path $claimsDir -Filter '*.claim' -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match "^0*$([regex]::Escape($numericId))-.*\.claim$" }
        if ($wildcard.Count -eq 1) { $claimMatches = $wildcard }
    }
}

if ($claimMatches.Count -ge 1) {
    foreach ($claim in $claimMatches) {
        Remove-Item -Path $claim.FullName -Force
        Write-Info "Removed claim $($claim.Name)"
    }
}
else {
    Write-Info "No claim file for id $numericId (already released or never claimed) - nothing to remove."
}

# --- Step 3: prune the PLAN.md line, CAS-style (fresh read immediately before write) ---

if (Test-Path $planPath) {
    $lines = Get-Content -Path $planPath
    $lineIdPattern = "^\s*-\s*\[\s*\]\s*0*$([regex]::Escape($numericId))(\s|$)"
    $matchCount = ($lines | Where-Object { $_ -match $lineIdPattern }).Count

    if ($matchCount -eq 0) {
        Write-Info "No PLAN.md line found for todo $Id - nothing to prune."
    }
    elseif ($matchCount -gt 1) {
        # Id shared by >1 PLAN.md line (duplicate-id backlog): the label alone
        # isn't authoritative per this file's own contract, so don't guess which
        # line belongs to the file we just completed - that could delete a still-open
        # sibling's line. Leave both; the caller prunes the right one by hand.
        Write-Info "PLAN.md has $matchCount lines for id $numericId (duplicate-id backlog) - not auto-pruning, remove the correct line by hand."
    }
    else {
        $keptLines = $lines | Where-Object { $_ -notmatch $lineIdPattern }
        Set-Content -Path $planPath -Value $keptLines -Encoding utf8
        Write-Info "Pruned PLAN.md line(s) for todo $Id"
    }
}
else {
    Write-Info "No PLAN.md at $planPath - skipping prune step."
}

Write-Info "Completion bookkeeping done for todo $Id."
