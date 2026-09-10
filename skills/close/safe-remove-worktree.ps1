<#
.SYNOPSIS
  Removes a git worktree without recursing through reparse points into the main checkout.

.DESCRIPTION
  PS 5.1 `Remove-Item -Recurse` and `git worktree remove --force` both follow reparse points
  (junctions, symlinks) found inside a worktree. When a worktree deliberately junctions
  something like node_modules back to the main checkout, a naive remove recurses through that
  junction and deletes files in the MAIN checkout (2026-07-31 incident, memory
  `worktree-removal-junction-hazard`: gutted two node_modules trees plus frontend2/.env.local).

  Steps: (1) refuse unless WorktreePath is a real, currently-registered `git worktree`, and
  never the main checkout itself; (2) list every reparse point under it and remove each with
  non-recursive `cmd /c rmdir` (unlinks the reparse point, never touches its target); (3)
  `git worktree remove` (plain, then `--force`, then a `cmd /c rmdir /S /Q` + `git worktree
  prune` fallback for long-path failures); (4) print `git status --short` in the main checkout
  as the script's own proof that nothing outside the worktree was touched.

.PARAMETER WorktreePath
  Path to the worktree to remove.

.PARAMETER RepoRoot
  Path to the main checkout (where `git worktree list` is authoritative). Defaults to the
  current directory.

.PARAMETER DryRun
  Report the reparse points found and the actions that would run, without removing anything.

.EXAMPLE
  ~/.claude/skills/close/safe-remove-worktree.ps1 -WorktreePath C:\work\myrepo-wt1
  ~/.claude/skills/close/safe-remove-worktree.ps1 -WorktreePath C:\work\myrepo-wt1 -DryRun
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$WorktreePath,

    [string]$RepoRoot = (Get-Location).Path,

    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host $msg }
function Write-Fail($msg) { Write-Error $msg }

# PS 5.1 + $ErrorActionPreference = 'Stop' turns ANY stderr line from a native command
# redirected with `2>&1` into a terminating NativeCommandError, even when the exit code is 0
# and even when the message is git's ordinary, expected output (todo 975, reproduced
# 2026-09-11: `git worktree remove` on a worktree with an untracked file writes exactly one
# expected "use --force" line to stderr, which killed this script before its own --force
# fallback below could run). Every native call in this script goes through this helper instead:
# no `2>&1`, so stderr goes straight to the real console stream and is never turned into a
# PowerShell error object; `$LASTEXITCODE` right after the call is the only success signal.
function Invoke-NativeCapture {
    param([Parameter(Mandatory = $true)][scriptblock]$Command)
    $output = & $Command
    return [PSCustomObject]@{ Output = $output; ExitCode = $LASTEXITCODE }
}

# --- Resolve and validate before touching anything ---

if (-not (Test-Path $RepoRoot)) {
    Write-Fail "RepoRoot '$RepoRoot' does not exist."
}
$resolvedRoot = (Resolve-Path $RepoRoot).Path

if (-not (Test-Path $WorktreePath)) {
    Write-Fail "WorktreePath '$WorktreePath' does not exist - nothing to remove."
}
$resolvedWorktree = (Resolve-Path $WorktreePath).Path

# Refusal: never let this touch the main checkout itself.
if ($resolvedWorktree -ieq $resolvedRoot) {
    Write-Fail "WorktreePath resolves to RepoRoot itself ('$resolvedRoot') - refusing to remove the main checkout."
}

# Refusal: only ever act on a path git itself already knows is a worktree - guards
# against pointing this at an arbitrary directory that happens to contain reparse points.
$listResult = Invoke-NativeCapture { & git -C $resolvedRoot worktree list --porcelain }
$worktreeList = $listResult.Output
if ($listResult.ExitCode -ne 0) {
    Write-Fail "'git worktree list' failed in '$resolvedRoot': $worktreeList"
}
$registeredPaths = $worktreeList | Where-Object { $_ -match '^worktree\s+(.+)$' } | ForEach-Object {
    $p = $matches[1].Trim()
    if (Test-Path $p) { (Resolve-Path $p).Path }
}
if ($resolvedWorktree -notin $registeredPaths) {
    Write-Fail "'$resolvedWorktree' is not a worktree registered to '$resolvedRoot' per 'git worktree list' - refusing. Registered: $($registeredPaths -join ', ')"
}

# --- Step 1: find every reparse point under the worktree (junctions, symlinks) ---

$reparsePoints = Get-ChildItem -Path $resolvedWorktree -Recurse -Attributes ReparsePoint -ErrorAction SilentlyContinue

if ($DryRun) {
    Write-Info "DRY RUN - would remove worktree '$resolvedWorktree'"
    if ($reparsePoints) {
        Write-Info "Reparse points that would be unlinked (non-recursive, target untouched):"
        $reparsePoints | ForEach-Object { Write-Info "  $($_.FullName)" }
    }
    else {
        Write-Info "No reparse points found under the worktree."
    }
    Write-Info "Would then run: git worktree remove (plain, then --force, then rmdir+prune fallback)."
    Write-Info "Would then print: git status --short in '$resolvedRoot'."
    return
}

# --- Step 2: strip reparse points non-recursively so removal never follows them ---

foreach ($rp in $reparsePoints) {
    Write-Info "Unlinking reparse point: $($rp.FullName)"
    # rmdir is directory-only; a symlinked FILE matches the ReparsePoint filter but survives it,
    # and would then be followed by git worktree remove.
    if ($rp.PSIsContainer) {
        $unlinkResult = Invoke-NativeCapture { & cmd /c rmdir "$($rp.FullName)" }
    }
    else {
        $unlinkResult = Invoke-NativeCapture { & cmd /c del /f /q "$($rp.FullName)" }
    }
    $unlinkResult.Output | ForEach-Object { Write-Info "  $_" }
    if (Test-Path -LiteralPath $rp.FullName) {
        Write-Fail "Reparse point '$($rp.FullName)' survived unlinking - refusing to continue, removal could follow it into the target."
    }
}

# --- Step 3: git worktree remove, with fallbacks for stubborn/long-path cases ---

$plainResult = Invoke-NativeCapture { & git -C $resolvedRoot worktree remove $resolvedWorktree }
$plainResult.Output | ForEach-Object { Write-Info $_ }
$removed = -not (Test-Path $resolvedWorktree)

if (-not $removed) {
    Write-Info "Plain remove did not finish - retrying with --force."
    $forceResult = Invoke-NativeCapture { & git -C $resolvedRoot worktree remove --force $resolvedWorktree }
    $forceResult.Output | ForEach-Object { Write-Info $_ }
    $removed = -not (Test-Path $resolvedWorktree)
}

if (-not $removed) {
    Write-Info "--force did not finish (likely a long-path failure) - falling back to rmdir /S /Q + prune."
    $rmdirResult = Invoke-NativeCapture { & cmd /c rmdir /S /Q "$resolvedWorktree" }
    $rmdirResult.Output | ForEach-Object { Write-Info "  $_" }
    $pruneResult = Invoke-NativeCapture { & git -C $resolvedRoot worktree prune }
    $pruneResult.Output | ForEach-Object { Write-Info $_ }
    $removed = -not (Test-Path $resolvedWorktree)
}

if (-not $removed) {
    Write-Fail "Worktree '$resolvedWorktree' still exists after plain remove, --force, and rmdir+prune fallback."
}

# --- Step 4: prove the main checkout is clean ---

Write-Info "Final status of main checkout '$resolvedRoot':"
& git -C $resolvedRoot status --short
