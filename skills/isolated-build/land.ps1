<#
.SYNOPSIS
  Lands work built in a scratch git worktree onto the main checkout's branch, without losing
  uncommitted files or screenshots to the removal step.

.DESCRIPTION
  Owns only the LAND half of the worktree build-and-land dance (todo 970). Worktree CREATION is a
  plain `git worktree add` plus `sv.ps1 ensure` (see SKILL.md's start section) - this script picks
  up from a worktree that already exists and already has work in it.

  Order matters and is fixed, not configurable, because the 2026-08-29 incident and the
  2026-09-07 half-removal were both caused by doing these in the wrong order:
    1. MOVE out screenshots and any uncommitted files FIRST, before anything that could delete
       them - move, not copy: once a file's content is safely in RepoRoot, leaving the original
       behind only guarantees `git worktree remove` refuses with "contains modified or untracked
       files", which cascades into point 4 below.
    2. Fast-forward TargetBranch onto the worktree's own branch, if it has commits TargetBranch
       lacks. Fast-forward only - this script creates no commit and no merge commit, so it never
       violates the "helper skills never commit" rule.
    3. Stop the supervised dev-server entry, if one is given - an open handle on the worktree
       directory is the most likely cause of the removal step's Permission Denied.
    4. Remove the worktree via safe-remove-worktree.ps1 (never reimplemented here - see that
       script's own header for why a naive remove is dangerous). That script's plain `git worktree
       remove` call throws a terminating NativeCommandError on ANY stderr under PS 5.1's
       `2>&1` + `$ErrorActionPreference='Stop'` combination (confirmed 2026-09-10), so it never
       reaches its own documented --force/rmdir+prune fallback whenever the worktree still has
       uncommitted content - step 1's move is what keeps the worktree git-clean so plain removal
       actually succeeds, rather than relying on that fallback chain firing.
    5. Delete the worktree's branch, but ONLY if step 4 actually removed the worktree AND step 2
       already carried its commits onto TargetBranch (or it had none) - deleting a branch still
       checked out in a half-removed worktree, or deleting one whose only commits were never
       landed, is exactly how work gets lost.

  A removal failure that survives step 1's cleanup (e.g. a genuine permission-denied lock, or
  cruft step 1 doesn't know about like build artifacts) is treated as an EXPECTED, non-fatal
  outcome of this script, per todo 970: report it, leave the directory on disk for a later sweep,
  and do not loop-retry or re-add the worktree. Branch deletion is skipped in that case (the
  branch is still in use by the surviving worktree).

.PARAMETER WorktreePath
  Path to the worktree being landed.

.PARAMETER RepoRoot
  Path to the main checkout. Defaults to the current directory. Must be a real checkout (not
  itself a worktree) whose CURRENTLY CHECKED OUT branch is TargetBranch - this script does not
  switch branches for you.

.PARAMETER TargetBranch
  Branch in RepoRoot to fast-forward. Defaults to RepoRoot's current branch.

.PARAMETER Branch
  The worktree's own branch. Defaults to whatever branch is checked out in WorktreePath.

.PARAMETER SupervisorId
  Optional `sv.ps1` proc id (e.g. `myrepo-feat:dev`) to stop before removal. Best-effort: a
  failure here is reported but does not abort the land.

.PARAMETER SkipRemoval
  Copy files, fast-forward, and stop the server, but leave worktree removal to the caller (e.g.
  the worktree was created via the harness's EnterWorktree tool, whose matching ExitWorktree owns
  disposal instead of safe-remove-worktree.ps1).

.PARAMETER DryRun
  Report what would happen without copying, merging, stopping, or removing anything.

.EXAMPLE
  ~/.claude/skills/isolated-build/land.ps1 -WorktreePath C:\work\myrepo-feat -RepoRoot C:\work\myrepo -SupervisorId myrepo-feat:dev
  ~/.claude/skills/isolated-build/land.ps1 -WorktreePath C:\work\myrepo-feat -DryRun
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$WorktreePath,

    [string]$RepoRoot = (Get-Location).Path,

    [string]$TargetBranch,
    [string]$Branch,
    [string]$SupervisorId,

    [switch]$SkipRemoval,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host $msg }
function Write-Fail($msg) { Write-Error $msg }

# --- Resolve and validate before touching anything ---

if (-not (Test-Path $RepoRoot)) { Write-Fail "RepoRoot '$RepoRoot' does not exist." }
$resolvedRoot = (Resolve-Path $RepoRoot).Path

if (-not (Test-Path $WorktreePath)) { Write-Fail "WorktreePath '$WorktreePath' does not exist." }
$resolvedWorktree = (Resolve-Path $WorktreePath).Path

if ($resolvedWorktree -ieq $resolvedRoot) {
    Write-Fail "WorktreePath resolves to RepoRoot itself ('$resolvedRoot') - nothing to land."
}

$worktreeList = & git -C $resolvedRoot worktree list --porcelain 2>&1
if ($LASTEXITCODE -ne 0) { Write-Fail "'git worktree list' failed in '$resolvedRoot': $worktreeList" }
$registeredPaths = $worktreeList | Where-Object { $_ -match '^worktree\s+(.+)$' } | ForEach-Object {
    $p = $matches[1].Trim()
    if (Test-Path $p) { (Resolve-Path $p).Path }
}
if ($resolvedWorktree -notin $registeredPaths) {
    Write-Fail "'$resolvedWorktree' is not a worktree registered to '$resolvedRoot' - refusing. Registered: $($registeredPaths -join ', ')"
}

if (-not $TargetBranch) {
    $TargetBranch = (& git -C $resolvedRoot rev-parse --abbrev-ref HEAD).Trim()
}
if ($TargetBranch -eq 'HEAD') {
    Write-Fail "RepoRoot '$resolvedRoot' is in detached HEAD - checkout a real branch before landing onto it."
}
if (-not $Branch) {
    $Branch = (& git -C $resolvedWorktree rev-parse --abbrev-ref HEAD).Trim()
}

Write-Info "Landing '$resolvedWorktree' (branch '$Branch') onto '$resolvedRoot' (branch '$TargetBranch')."

# --- Step 1: copy out screenshots and uncommitted files, before anything destructive ---

$screenshotsSrc = Join-Path $resolvedWorktree '.for_bepy\screenshots'
if (Test-Path $screenshotsSrc) {
    $screenshotsDst = Join-Path $resolvedRoot '.for_bepy\screenshots'
    if ($DryRun) {
        Write-Info "DRY RUN - would move '$screenshotsSrc' -> '$screenshotsDst'"
    }
    else {
        New-Item -ItemType Directory -Force -Path $screenshotsDst | Out-Null
        Copy-Item -Path (Join-Path $screenshotsSrc '*') -Destination $screenshotsDst -Recurse -Force
        Remove-Item -Path $screenshotsSrc -Recurse -Force
        Write-Info "Moved screenshots: '$screenshotsSrc' -> '$screenshotsDst'"
    }
}

# MOVE, not copy: once a file's content is safely in RepoRoot, leaving the original behind in the
# worktree only guarantees `git worktree remove` (no --force) refuses with "contains modified or
# untracked files" - and safe-remove-worktree.ps1's own plain-remove call throws a terminating
# NativeCommandError on that stderr (PS 5.1 promotes native stderr through `2>&1` under
# $ErrorActionPreference='Stop'), so it never reaches its own --force/rmdir+prune fallback chain
# (reproduced 2026-09-10, see this skill's own end-to-end proof). Moving leaves the worktree
# git-clean so plain removal succeeds normally, sidestepping that bug for the common case.
$statusLines = & git -C $resolvedWorktree status --porcelain=v1
$copied = @()
$deletedInWorktree = @()
foreach ($line in $statusLines) {
    if (-not $line) { continue }
    $code = $line.Substring(0, 2)
    $rest = $line.Substring(3)
    if ($rest -match '^(.+) -> (.+)$') { $rest = $matches[2] }  # rename: land the new path
    if ($code -match 'D') {
        $deletedInWorktree += $rest
        continue
    }
    $srcFile = Join-Path $resolvedWorktree $rest
    $dstFile = Join-Path $resolvedRoot $rest
    if (-not (Test-Path $srcFile)) { continue }
    if ($DryRun) {
        Write-Info "DRY RUN - would move '$rest'"
    }
    else {
        New-Item -ItemType Directory -Force -Path (Split-Path $dstFile -Parent) | Out-Null
        Copy-Item -Path $srcFile -Destination $dstFile -Force
        Remove-Item -Path $srcFile -Force
    }
    $copied += $rest
}
if ($copied.Count -gt 0) {
    $verb = if ($DryRun) { "Would move" } else { "Moved" }
    Write-Info "$verb $($copied.Count) uncommitted file(s) into '$resolvedRoot':"
    $copied | ForEach-Object { Write-Info "  $_" }
}
if ($deletedInWorktree.Count -gt 0) {
    Write-Info "NOTE: $($deletedInWorktree.Count) file(s) deleted in the worktree were NOT mirrored (deletion is destructive, left for a human/`/commit` to decide):"
    $deletedInWorktree | ForEach-Object { Write-Info "  $_" }
}

# --- Step 2: fast-forward TargetBranch onto Branch, if Branch has commits TargetBranch lacks ---

$aheadRaw = & git -C $resolvedRoot rev-list "$TargetBranch..$Branch" 2>&1
$ffMerged = $false
if ($LASTEXITCODE -eq 0 -and $aheadRaw) {
    $aheadCount = ($aheadRaw | Measure-Object).Count
    Write-Info "'$Branch' has $aheadCount commit(s) not on '$TargetBranch'."
    if ($DryRun) {
        Write-Info "DRY RUN - would attempt: git -C '$resolvedRoot' merge --ff-only $Branch"
        $ffMerged = $true  # assume success for the dry-run branch-delete preview below
    }
    else {
        $mergeOut = & git -C $resolvedRoot merge --ff-only $Branch 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Info "Fast-forwarded '$TargetBranch' onto '$Branch': $mergeOut"
            $ffMerged = $true
        }
        else {
            Write-Info "Fast-forward failed (branches have diverged) - leaving '$Branch' as-is, NOT force-merging or rebasing:"
            Write-Info "  $mergeOut"
        }
    }
}
else {
    Write-Info "'$Branch' has no commits ahead of '$TargetBranch' (all work was uncommitted, or already landed)."
    $ffMerged = $true  # nothing to lose by deleting the branch later
}

# --- Step 3: stop the supervised entry, best-effort ---

if ($SupervisorId) {
    $svPath = Join-Path (Split-Path $PSScriptRoot -Parent) 'supervised-run\sv.ps1'
    if ($DryRun) {
        Write-Info "DRY RUN - would run: $svPath stop -Id $SupervisorId"
    }
    else {
        try {
            & powershell -File $svPath stop -Id $SupervisorId 2>&1 | ForEach-Object { Write-Info "  $_" }
        }
        catch {
            Write-Info "Could not stop supervised entry '$SupervisorId' (non-fatal, continuing): $_"
        }
    }
}

# --- Step 4: remove the worktree via the existing script, never reimplemented here ---

$removed = $false
if ($SkipRemoval) {
    Write-Info "SkipRemoval set - leaving worktree removal to the caller."
}
elseif ($DryRun) {
    Write-Info "DRY RUN - would run: safe-remove-worktree.ps1 -WorktreePath '$resolvedWorktree' -RepoRoot '$resolvedRoot'"
    $removed = $true
}
else {
    $removeScript = Join-Path (Split-Path $PSScriptRoot -Parent) 'close\safe-remove-worktree.ps1'
    try {
        & $removeScript -WorktreePath $resolvedWorktree -RepoRoot $resolvedRoot
        $removed = -not (Test-Path $resolvedWorktree)
    }
    catch {
        Write-Info "Worktree removal did not complete - treating this as the EXPECTED half-failure documented in todo 970, not retrying:"
        Write-Info "  $_"
        Write-Info "The directory may still exist on disk; it is left for a later manual sweep."
    }
}

# --- Step 5: delete the branch, only if removal succeeded and its commits are safe ---

if ($removed -and -not $SkipRemoval) {
    if ($ffMerged) {
        if ($DryRun) {
            Write-Info "DRY RUN - would run: git -C '$resolvedRoot' branch -D $Branch"
        }
        else {
            & git -C $resolvedRoot branch -D $Branch 2>&1 | ForEach-Object { Write-Info $_ }
        }
    }
    else {
        Write-Info "NOT deleting branch '$Branch' - it still has commits not on '$TargetBranch' (fast-forward failed above). Resolve that first."
    }
}
elseif (-not $SkipRemoval) {
    Write-Info "NOT deleting branch '$Branch' - the worktree removal did not complete, so the branch is likely still checked out there."
}

# --- Final proof ---

Write-Info "`nFinal state:"
& git -C $resolvedRoot worktree list
Write-Info "Last commit on '$TargetBranch':"
& git -C $resolvedRoot log --oneline -1 $TargetBranch
