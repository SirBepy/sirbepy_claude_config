<#
.SYNOPSIS
Proves a new test fails against pre-fix code, without touching the live working tree.

.DESCRIPTION
Replaces the hand-rolled "git stash push -- <fix paths> && test && git stash pop" dance.
Checks out HEAD into a detached worktree (same trick as /commit step 6's baseline
comparison), overlays every OTHER uncommitted change (new test files included) on top of
it, but leaves FixPaths at their committed, pre-fix state. The test then runs against
pre-fix code by construction. Never stashes, resets or checks out anything in the live
tree, so a peer session's own uncommitted work is read but never mutated.

.PARAMETER FixPaths
Repo-relative or absolute paths that make up the fix. Each must already be dirty
(tracked-modified, staged or under an already-dirty directory) - a clean path here would
silently no-op instead of reverting anything.

.PARAMETER TestCommand
The command to run inside the pre-fix worktree, e.g. "pytest tests/test_foo.py -k bar".

.EXAMPLE
./red-check.ps1 -FixPaths hooks/foo.py -TestCommand "python hooks/test_foo.py"
#>
param(
    [Parameter(Mandatory)][string[]]$FixPaths,
    [Parameter(Mandatory)][string]$TestCommand
)

$ErrorActionPreference = 'Stop'

function ConvertTo-RepoRelative([string]$Path, [string]$RepoRoot) {
    $resolved = Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue
    $abs = if ($resolved) { $resolved.Path } elseif ([System.IO.Path]::IsPathRooted($Path)) { $Path } else { Join-Path (Get-Location) $Path }
    $abs = $abs -replace '\\', '/'
    $root = $RepoRoot.TrimEnd('/')
    if ($abs -notlike "$root/*") { throw "Path '$Path' is outside the repo root '$root'." }
    return $abs.Substring($root.Length + 1)
}

function Test-UnderFixPath([string]$DirtyPath, [string[]]$FixRel) {
    foreach ($fp in $FixRel) {
        if ($DirtyPath -eq $fp -or $DirtyPath -like "$fp/*") { return $true }
    }
    return $false
}

$repoRoot = (git rev-parse --show-toplevel).Trim()
if (-not $repoRoot) { throw "Not inside a git repository." }

$fixRel = $FixPaths | ForEach-Object { ConvertTo-RepoRelative $_ $repoRoot }

# Dirty set = index + worktree + untracked, relative paths only (rename lines keep the new side).
$dirty = @()
foreach ($line in (git -C $repoRoot status --porcelain)) {
    if ($line.Length -lt 4) { continue }
    $p = $line.Substring(3).Trim()
    if ($p -match '^(.+) -> (.+)$') { $p = $Matches[2] }
    $dirty += $p
}

foreach ($fp in $fixRel) {
    $covered = $dirty | Where-Object { $_ -eq $fp -or $_ -like "$fp/*" }
    if (-not $covered) {
        throw "FixPath '$fp' has no uncommitted changes - refusing to run (see todo 887: a red-check must only revert paths the caller actually touched)."
    }
}

$tmp = Join-Path $env:TEMP "red-check-$([guid]::NewGuid().ToString('N'))"
$worktreeCreated = $false
try {
    git -C $repoRoot worktree add --detach $tmp HEAD | Out-Null
    $worktreeCreated = $true

    # Overlay every dirty file except the fix itself - new test files ride along,
    # the fix paths stay at their committed (pre-fix) content.
    foreach ($p in $dirty) {
        if (Test-UnderFixPath $p $fixRel) { continue }
        $src = Join-Path $repoRoot $p
        if (-not (Test-Path -LiteralPath $src)) { continue }
        $dest = Join-Path $tmp $p
        New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
        Copy-Item -LiteralPath $src -Destination $dest -Force
    }

    # Native stderr under $ErrorActionPreference='Stop' turns a non-zero exit into a
    # terminating exception before $LASTEXITCODE is even read - relax it for this call only.
    Push-Location $tmp
    $prevEAP = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = Invoke-Expression $TestCommand 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $prevEAP
        Pop-Location
    }

    Write-Output $output
    if ($exitCode -eq 0) {
        throw "Test PASSED against pre-fix code - not a valid regression guard. Fix paths: $($fixRel -join ', ')"
    }
    Write-Output "RED confirmed: test failed against pre-fix code (exit $exitCode)."
} finally {
    if ($worktreeCreated) {
        git -C $repoRoot worktree remove $tmp --force 2>&1 | Out-Null
    }
}
