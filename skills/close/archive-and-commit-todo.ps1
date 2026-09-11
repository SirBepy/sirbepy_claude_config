<#
.SYNOPSIS
  Archives one .claude/todos/ backlog item and commits it, in a single call (todo 978).

.DESCRIPTION
  Collapses the four hand-assembled steps a `/close` Phase 1 run repeats per todo - run
  complete-todo.ps1, `git add` the new done\ path, hand-build the three-part pathspec
  (changed files + done\ destination + the now-deleted .claude\todos\ source), then invoke
  commit-pathspec.sh - into one call. The caller supplies the todo id, an optional note, a
  commit message, and the files the work itself touched; this script derives the other two
  pathspec entries itself and never lets the deleted-source half go unnamed (todo 932's bug).

  Never reimplements the move: archival is delegated to complete-todo.ps1 exactly as it
  would be run by hand. This script only (1) resolves which backlog file will move, before
  calling complete-todo.ps1, so it knows the exact filename and pre-move tracked state, (2)
  calls complete-todo.ps1, (3) builds the pathspec, (4) shells out to commit-pathspec.sh.

  Source-tracked detection mirrors mega-todos/archive-batch.ps1's own fix for todo 932
  exactly: Move-Item (which complete-todo.ps1 uses) never touches the git index, so
  `git ls-files --error-unmatch` on the pre-move path still answers correctly - tracked
  before the move - even though the working-tree file is already gone. An untracked
  source (never committed before archival) is correctly left out: there is no deletion to
  stage for a file git never knew about.

  --expect-branch/--expect-sha default to this repo's CURRENT branch and HEAD, captured
  before complete-todo.ps1 runs, so the guard covers complete-todo.ps1's own file/PLAN.md
  writes too. Pass them explicitly when chaining several of these calls in one script and
  you already hold an earlier "expected" pair from before the chain started - the guard is
  only as strong as how early its expectation was captured, and a caller running several
  archivals back to back knows that history better than a fresh capture right before each
  individual call would.

.PARAMETER Id
  The numeric todo id (or full "<id>-<slug>" stem), same as complete-todo.ps1's -Id.
  Must resolve to exactly one file in the LIVE backlog (.claude\todos\, not done\) - this
  script archives a todo, it does not re-commit one that is already archived. If the todo
  is already in done\, there is nothing left to move: call commit-pathspec.sh directly.

.PARAMETER Slug
  Optional disambiguator, passed through to complete-todo.ps1 unchanged.

.PARAMETER Note
  Optional completion note, passed through to complete-todo.ps1 unchanged.

.PARAMETER Message
  The commit message.

.PARAMETER Files
  The files the underlying work touched (repo-relative paths), beyond the archive move
  itself. May be empty when the only content of this commit is the archive move.

.PARAMETER RepoRoot
  Project root containing .claude/todos/. Defaults the same way complete-todo.ps1 does.

.PARAMETER ExpectBranch
  Passed to commit-pathspec.sh. Defaults to the current branch, read before archiving.

.PARAMETER ExpectSha
  Passed to commit-pathspec.sh. Defaults to the current HEAD, read before archiving.

.PARAMETER OwnSince
  Passed through to commit-pathspec.sh's --own-since verbatim.

.PARAMETER Own
  Passed through to commit-pathspec.sh's --own verbatim.

.PARAMETER Force
  Passed through to commit-pathspec.sh's --force verbatim (e.g. "coverage" or "head-guard").

.OUTPUTS
  Prints commit-pathspec.sh's own output verbatim, then the resulting full commit sha (its
  own last line) on success. Exits 0 on a landed commit, 1 on a refused check (nothing
  committed - matches commit-pathspec.sh's own exit code), 2 on a usage/setup error
  (matches commit-pathspec.sh's own exit code for "could not run").

.EXAMPLE
  ~/.claude/skills/close/archive-and-commit-todo.ps1 -Id 978 `
    -Note "shipped --own-since and this wrapper" `
    -Message "FEAT: archive-and-commit-todo wrapper, --own-since (todo 978)" `
    -Files skills/commit/commit-pathspec.sh, skills/commit/test_commit_pathspec.sh, skills/close/archive-and-commit-todo.ps1

.EXAMPLE
  ~/.claude/skills/close/archive-and-commit-todo.ps1 -Id 434 -Slug chat-row-style-decide-and-delete-loser `
    -Message "CHORE: archive todo 434" -Files @() -OwnSince a1b2c3d
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$Id,

    [string]$Slug,

    [string]$Note,

    [Parameter(Mandatory = $true)]
    [string]$Message,

    [string[]]$Files = @(),

    [string]$RepoRoot,

    [string]$ExpectBranch,

    [string]$ExpectSha,

    [string]$OwnSince,

    [string]$Own,

    [string]$Force
)

$ErrorActionPreference = 'Stop'

if (-not $RepoRoot) {
    $gitRoot = $null
    try {
        $gitRoot = (git rev-parse --show-toplevel 2>$null)
        if ($LASTEXITCODE -ne 0) { $gitRoot = $null }
    }
    catch { $gitRoot = $null }
    $RepoRoot = if ($gitRoot) { ($gitRoot -replace '/', '\') } else { (Get-Location).Path }
}

function Write-Info($msg) { Write-Host "[$RepoRoot] $msg" }

# Captured BEFORE complete-todo.ps1 runs, so the guard also covers its own file/PLAN.md
# writes, not just the window between archiving and this script's own commit-pathspec.sh
# call.
if (-not $ExpectBranch) {
    $ExpectBranch = (git -C $RepoRoot rev-parse --abbrev-ref HEAD 2>$null)
    if ($LASTEXITCODE -ne 0 -or -not $ExpectBranch) {
        Write-Error "[$RepoRoot] archive-and-commit-todo.ps1: could not resolve the current branch to default -ExpectBranch."
        exit 2
    }
}
if (-not $ExpectSha) {
    $ExpectSha = (git -C $RepoRoot rev-parse HEAD 2>$null)
    if ($LASTEXITCODE -ne 0 -or -not $ExpectSha) {
        Write-Error "[$RepoRoot] archive-and-commit-todo.ps1: could not resolve HEAD to default -ExpectSha."
        exit 2
    }
}

$todosDir = Join-Path $RepoRoot '.claude\todos'
$doneDir  = Join-Path $todosDir 'done'

if (-not (Test-Path $todosDir)) {
    Write-Error "[$RepoRoot] archive-and-commit-todo.ps1: no .claude\todos found (looked for '$todosDir')."
    exit 2
}

# --- Step 1: resolve the LIVE backlog file BEFORE archiving, so its exact name and
# pre-move tracked state are known. Read-only - never reimplements the move itself. ---
. (Join-Path $PSScriptRoot '_shared.ps1')

$resolved = Resolve-TodoFile -Dir $todosDir -RawId $Id -Slug $Slug
$liveMatches = $resolved.Matches
if ($liveMatches -and $resolved.Slug) {
    $slugPattern = "^0*$([regex]::Escape($resolved.NumericId))-$([regex]::Escape($resolved.Slug))\.md$"
    $liveMatches = $liveMatches | Where-Object { $_.Name -match $slugPattern }
}
if (-not $liveMatches -or @($liveMatches).Count -ne 1) {
    $count = @($liveMatches).Count
    Write-Error "[$RepoRoot] archive-and-commit-todo.ps1: expected exactly 1 LIVE backlog match for id '$Id' in $todosDir, found $count. This script only archives a todo that is still live - if '$Id' is already in done\, there is nothing to move: call commit-pathspec.sh directly with your changed files."
    exit 1
}
$sourceFile = $liveMatches[0]
$sourceRelPosix = ".claude/todos/$($sourceFile.Name)"
$destRelPosix   = ".claude/todos/done/$($sourceFile.Name)"
$destFullPath   = Join-Path $doneDir $sourceFile.Name

# --- Step 2: archive via complete-todo.ps1 - never reimplemented here. ---
$completeScript = Join-Path $PSScriptRoot 'complete-todo.ps1'
$callArgs = @{ Id = $Id; RepoRoot = $RepoRoot }
if ($Slug) { $callArgs['Slug'] = $Slug }
if ($Note) { $callArgs['Note'] = $Note }
try {
    & $completeScript @callArgs
}
catch {
    Write-Error "[$RepoRoot] archive-and-commit-todo.ps1: complete-todo.ps1 failed for id '$Id' - $($_.Exception.Message)"
    exit 1
}

if (-not (Test-Path $destFullPath)) {
    Write-Error "[$RepoRoot] archive-and-commit-todo.ps1: complete-todo.ps1 reported success but '$destFullPath' does not exist - refusing to commit."
    exit 2
}

# --- Step 3: derive the three-part pathspec. A raw Move-Item never touches the git index,
# so `git ls-files --error-unmatch` on the ORIGINAL path still answers "was this tracked"
# correctly after the move (todo 932's fix, mirrored here rather than reinvented). ---
$sourceTracked = $false
try {
    git -C $RepoRoot ls-files --error-unmatch -- $sourceFile.FullName 2>$null | Out-Null
    $sourceTracked = ($LASTEXITCODE -eq 0)
}
catch { $sourceTracked = $false }

$pathspec = New-Object System.Collections.Generic.List[string]
foreach ($f in $Files) {
    if ($f) { $pathspec.Add(($f -replace '\\', '/')) }
}
if ($sourceTracked) { $pathspec.Add($sourceRelPosix) }
$pathspec.Add($destRelPosix)

Write-Info "Pathspec for commit-pathspec.sh: $($pathspec -join ', ')"
if (-not $sourceTracked) {
    Write-Info "Note: '$sourceRelPosix' was untracked before archiving (never committed) - no deletion to stage for it, matching complete-todo.ps1/archive-batch.ps1's own todo-848 exemption."
}

# --- Step 4: shell out to commit-pathspec.sh. It is a bash script always invoked through a
# real Git Bash, never bare `bash` on Windows (that resolves to the broken WSL shim on CI -
# ci/run_all.py's own _bash_exe() documents the same fix). All paths handed to it are
# forward-slash: bash treats a Windows backslash as an escape character, not a separator. ---
function Resolve-BashExe {
    if ($env:OS -ne 'Windows_NT') { return 'bash' }
    foreach ($candidate in @('C:\Program Files\Git\bin\bash.exe', 'C:\Program Files\Git\usr\bin\bash.exe')) {
        if (Test-Path $candidate) { return $candidate }
    }
    $found = (Get-Command bash -ErrorAction SilentlyContinue).Source
    if ($found -and $found -notmatch 'system32') { return $found }
    return 'bash'
}

$bashExe = Resolve-BashExe
$commitScript = (Resolve-Path (Join-Path $PSScriptRoot '..\commit\commit-pathspec.sh')).Path -replace '\\', '/'
$repoRootPosix = $RepoRoot -replace '\\', '/'

$bashArgs = @(
    $commitScript,
    '-C', $repoRootPosix,
    '--expect-branch', $ExpectBranch,
    '--expect-sha', $ExpectSha
)
if ($Own) { $bashArgs += @('--own', $Own) }
if ($OwnSince) { $bashArgs += @('--own-since', $OwnSince) }
if ($Force) { $bashArgs += @('--force', $Force) }
$bashArgs += @('-m', $Message, '--')
$bashArgs += $pathspec.ToArray()

& $bashExe @bashArgs
$commitExit = $LASTEXITCODE
exit $commitExit
