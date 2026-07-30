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
  "07-fix-auth-redirect.md").

.PARAMETER RepoRoot
  Project root containing .claude/todos/. Defaults to the current directory.

.EXAMPLE
  ~/.claude/skills/close/complete-todo.ps1 -Id 286
  ~/.claude/skills/close/complete-todo.ps1 -Id 07 -RepoRoot C:\Users\joe\Projects\my-app
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Id,

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

$idPattern = "^0*$([regex]::Escape($Id))-.*\.md$"

# --- Step 1: move the backlog file to done/ (or detect it's already there) ---

$backlogMatches = Get-ChildItem -Path $todosDir -Filter '*.md' -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match $idPattern }

if ($backlogMatches -and $backlogMatches.Count -gt 1) {
    Write-Fail "Ambiguous id '$Id': multiple files match in $todosDir - $($backlogMatches.Name -join ', ')"
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

    if ($doneMatches.Count -ge 1) {
        Write-Info "Todo $Id already completed (found in done\$($doneMatches[0].Name)) - skipping move."
    }
    else {
        Write-Fail "No todo file matching id '$Id' found in $todosDir or $doneDir."
    }
}

# --- Step 2: release the claim, if any ---

$claimMatches = @()
if (Test-Path $claimsDir) {
    $claimMatches = Get-ChildItem -Path $claimsDir -Filter '*.claim' -File -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match "^0*$([regex]::Escape($Id))\.claim$" }
}

if ($claimMatches.Count -ge 1) {
    foreach ($claim in $claimMatches) {
        Remove-Item -Path $claim.FullName -Force
        Write-Info "Removed claim $($claim.Name)"
    }
}
else {
    Write-Info "No claim file for id $Id (already released or never claimed) - nothing to remove."
}

# --- Step 3: prune the PLAN.md line, CAS-style (fresh read immediately before write) ---

if (Test-Path $planPath) {
    $lines = Get-Content -Path $planPath
    $lineIdPattern = "^\s*-\s*\[\s*\]\s*0*$([regex]::Escape($Id))(\s|$)"
    $keptLines = $lines | Where-Object { $_ -notmatch $lineIdPattern }

    if ($keptLines.Count -ne $lines.Count) {
        Set-Content -Path $planPath -Value $keptLines -Encoding utf8
        Write-Info "Pruned PLAN.md line(s) for todo $Id"
    }
    else {
        Write-Info "No PLAN.md line found for todo $Id - nothing to prune."
    }
}
else {
    Write-Info "No PLAN.md at $planPath - skipping prune step."
}

Write-Info "Completion bookkeeping done for todo $Id."
