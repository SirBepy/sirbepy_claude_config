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

.PARAMETER Note
  Optional completion note. Appended as a "- <text>" bullet under the todo file's ## Notes
  heading before it's moved to done/ - matching an existing heading, or creating one right
  after ## Acceptance (and before any ## Open questions block) when absent. Written BOM-less.

.EXAMPLE
  ~/.claude/skills/close/complete-todo.ps1 -Id 286
  ~/.claude/skills/close/complete-todo.ps1 -Id 07 -RepoRoot C:\Users\joe\Projects\my-app
  ~/.claude/skills/close/complete-todo.ps1 -Id 434 -Slug chat-row-style-decide-and-delete-loser
  ~/.claude/skills/close/complete-todo.ps1 -Id 434-chat-row-style-decide-and-delete-loser
  ~/.claude/skills/close/complete-todo.ps1 -Id 286 -Note "completed, commit abc1234"
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Id,

    [string]$Slug,

    [string]$RepoRoot = (Get-Location).Path,

    [string]$Note
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host $msg }
function Write-Fail($msg) { Write-Error $msg }

# Inserts "- $Note" under an existing "## Notes" heading, or creates one right after
# "## Acceptance" (naturally landing before any later "## Open questions" block) when
# no Notes heading exists yet. Line-array surgery, not a regex rewrite, so unrelated
# formatting survives untouched.
function Add-NoteBullet {
    param([string[]]$Lines, [string]$Note)

    $bullet = "- $Note"
    $notesIdx = ($Lines | Select-String -Pattern '^##\s*Notes\s*$').LineNumber
    if ($notesIdx) { $notesIdx = $notesIdx[0] - 1 }

    if ($notesIdx) {
        $insertAt = $Lines.Count
        for ($i = $notesIdx + 1; $i -lt $Lines.Count; $i++) {
            if ($Lines[$i] -match '^##\s') { $insertAt = $i; break }
        }
        while ($insertAt -gt $notesIdx + 1 -and $Lines[$insertAt - 1].Trim() -eq '') { $insertAt-- }
        $insert = @($bullet)
    }
    else {
        $accIdx = ($Lines | Select-String -Pattern '^##\s*Acceptance\s*$').LineNumber
        if (-not $accIdx) {
            # No Acceptance section either - append a fresh Notes section at EOF.
            return ($Lines + '' + '## Notes' + '' + $bullet)
        }
        $accIdx = $accIdx[0] - 1
        $insertAt = $Lines.Count
        for ($i = $accIdx + 1; $i -lt $Lines.Count; $i++) {
            if ($Lines[$i] -match '^##\s') { $insertAt = $i; break }
        }
        while ($insertAt -gt $accIdx + 1 -and $Lines[$insertAt - 1].Trim() -eq '') { $insertAt-- }
        $insert = @('', '## Notes', '', $bullet)
    }

    $before = if ($insertAt -gt 0) { $Lines[0..($insertAt - 1)] } else { @() }
    $after = if ($insertAt -lt $Lines.Count) { $Lines[$insertAt..($Lines.Count - 1)] } else { @() }
    return ($before + $insert + $after)
}

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

    if ($Note) {
        $rawContent = Get-Content -Path $todoFile.FullName -Raw
        $originalLines = $rawContent -split "`r?`n"
        $newLines = Add-NoteBullet -Lines $originalLines -Note $Note
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($todoFile.FullName, ($newLines -join "`r`n"), $utf8NoBom)
        Write-Info "Appended Notes bullet to $($todoFile.Name)"
    }

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
    # Can't distinguish never-claimed from already-released - no artifact records
    # release history. Warn anyway: per CLAUDE.md, claiming is non-negotiable, so
    # an absent claim at completion time is worth a reviewer's eyes either way.
    Write-Info "WARNING: todo $numericId is being completed with no claim on record - either it was executed without claiming, or the claim was released early (see close/ai-todos-format.md). Not blocking."
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
        $utf8NoBom = New-Object System.Text.UTF8Encoding $false
        [System.IO.File]::WriteAllText($planPath, (($keptLines -join "`r`n") + "`r`n"), $utf8NoBom)
        Write-Info "Pruned PLAN.md line(s) for todo $Id"
    }
}
else {
    Write-Info "No PLAN.md at $planPath - skipping prune step."
}

Write-Info "Completion bookkeeping done for todo $Id."
