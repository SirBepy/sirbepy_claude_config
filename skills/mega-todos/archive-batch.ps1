<#
.SYNOPSIS
  Archives a batch of completed .claude/todos/ items and emits the exact commit pathspec,
  replacing the hand-rolled per-todo loop in /mega-todos Step E.

.DESCRIPTION
  For each "<id>|<note>" item: resolves the id to exactly ONE live backlog file via
  close/_shared.ps1's Resolve-TodoFile (never a done/ glob, which is what broke twice -
  done/ accumulates every id ever used, so an id-prefix glob there can match a stale
  unrelated file), then runs close/complete-todo.ps1 -Id <id> -Note <note> on it.

  After each archive, names both halves of the move for the commit pathspec - the source
  under .claude/todos/ and the destination under done/ - per ai-todos-format.md's "Archiving
  is a two-path change" and the /commit step 8 coverage check it traces to. The source is
  emitted only when git already tracked it before the move (`git ls-files --error-unmatch`,
  checked against the index, not Test-Path against the now-gone working-tree file - todo
  932), so an untracked source (moved and gone, no delete to stage) never aborts the
  caller's git add the way it did for todo 848, while a tracked source's deletion always
  rides along in the pathspec instead of landing staged and unreported.

  Never commits. Prints the pathspec (plus PLAN.md, which complete-todo.ps1 prunes on every
  call) so the caller's own /commit runs its real gates - prefilter, branch guard, the
  Staged-pathspec coverage check - unchanged.

.PARAMETER Items
  One or more "<id>|<note>" pairs, e.g. "pc-0286|fixed the off-by-one". The id is
  device-prefixed (pc-0286) or a bare number (resolved by Resolve-TodoFile). The note half
  is optional - "pc-0286" alone completes with no Notes bullet appended.

.PARAMETER RepoRoot
  Project root containing .claude/todos/. Passed through to complete-todo.ps1 unchanged;
  defaults the same way it does (git toplevel, else cwd).

.OUTPUTS
  A PSCustomObject with Pathspec (string[] - existing destination paths plus any source
  path git tracked before its move) and Failures (string[], one line per id that could
  not be resolved or archived) written to the success stream.
  Exits 1 if any item failed, so the caller cannot mistake a partial batch for a clean one.

.EXAMPLE
  $result = & ~/.claude/skills/mega-todos/archive-batch.ps1 -Items "pc-0286|fixed the bug","pc-0097|done"
  $result.Pathspec
  $result.Failures
#>
param(
    [Parameter(Mandatory = $true)]
    [string[]]$Items,

    [string]$RepoRoot
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

$todosDir = Join-Path $RepoRoot '.claude\todos'
$doneDir = Join-Path $todosDir 'done'
$planPath = Join-Path $todosDir 'PLAN.md'
$completeScript = Join-Path $PSScriptRoot '..\close\complete-todo.ps1'

if (-not (Test-Path $todosDir)) {
    Write-Error "[$RepoRoot] No .claude\todos found (looked for '$todosDir')."
    exit 1
}

. (Join-Path $PSScriptRoot '..\close\_shared.ps1')

# Normalises an -Items id for the defence-in-depth check at the bottom, via the shared
# parser so no second copy of the id shape lives here. A labelled id compares as its
# canonical form (any padding), a bare number as a number matching ANY label (resolution
# picks the label - this device's first - so the check must not second-guess it), and a
# prefix-less stem as the whole stem.
function Add-InputId([string]$RawId) {
    $parsed = Parse-TodoId $RawId
    if ($null -eq $parsed) { [void]$inputIds.Add("stem:$($RawId.ToLowerInvariant())"); return }
    if ($parsed.Label) { [void]$inputIds.Add((Format-TodoId $parsed.Label $parsed.Number)) }
    else { [void]$inputIds.Add("num:$($parsed.Number)") }
}

# The same normalisation for a returned pathspec entry's filename: true when it traces
# back to an input id.
function Test-FilenameInInput([string]$Name) {
    $info = Get-TodoNameInfo $Name
    if ($null -eq $info) {
        return $inputIds.Contains("stem:$([System.IO.Path]::GetFileNameWithoutExtension($Name).ToLowerInvariant())")
    }
    return ($inputIds.Contains((Format-TodoId $info.Label $info.Number)) -or $inputIds.Contains("num:$($info.Number)"))
}

$pathspec = New-Object System.Collections.Generic.List[string]
$failures = New-Object System.Collections.Generic.List[string]
$inputIds = New-Object System.Collections.Generic.HashSet[string]

foreach ($item in $Items) {
    $parts = $item -split '\|', 2
    $id = $parts[0].Trim()
    $note = if ($parts.Count -gt 1) { $parts[1].Trim() } else { $null }
    Add-InputId $id

    # Resolve against the LIVE backlog only, before archiving moves the file -
    # done/ is never globbed here, which is the bug this script exists to kill.
    $resolved = Resolve-TodoFile -Dir $todosDir -RawId $id
    if ($resolved.Error) {
        $failures.Add("id '$id': $($resolved.Error)")
        continue
    }
    # Resolve-TodoFile already narrows by the slug in a full "<id>-<slug>" stem, so a
    # stem passed as -Id disambiguates a live-backlog id collision.
    $matches_ = @($resolved.Matches)
    if (-not $matches_ -or @($matches_).Count -ne 1) {
        $failures.Add("id '$id': $(@($matches_).Count) live backlog matches, expected 1 - not archived")
        continue
    }
    $sourcePath = $matches_[0].FullName
    $destPath = Join-Path $doneDir $matches_[0].Name

    # Hashtable splat, not array splat: complete-todo.ps1's -Id is [string[]], and an
    # array splat lets it greedily swallow the following -RepoRoot/-Note elements as
    # more of its own array instead of stopping at the next flag name.
    $callArgs = @{ Id = $id; RepoRoot = $RepoRoot }
    if ($note) { $callArgs['Note'] = $note }
    try {
        & $completeScript @callArgs | Out-Null
    }
    catch {
        $failures.Add("id '$id': complete-todo.ps1 failed - $($_.Exception.Message)")
        continue
    }

    # Move-Item (complete-todo.ps1:179) already ran, so the source is gone from disk -
    # Test-Path on it is always false, which silently dropped the deletion half of every
    # tracked move from the pathspec (todo 932). Move-Item never touches the git index,
    # so a source that was tracked before the move is STILL tracked (index still holds
    # the pre-move blob) even though the working-tree file is gone; `git ls-files
    # --error-unmatch` reads the index, not the working tree, so it answers "was this
    # tracked" correctly post-move where Test-Path cannot. An untracked source (todo 848)
    # still exits non-zero here and stays excluded, exactly as before.
    # Wrapped in try/catch, matching the $gitRoot resolution above: under
    # $ErrorActionPreference = 'Stop', a native command's stderr line becomes a
    # terminating error even when redirected, so an untracked path's expected
    # "did not match any file(s)" line must be caught, not just redirected.
    $sourceTracked = $false
    try {
        git -C $RepoRoot ls-files --error-unmatch -- $sourcePath 2>$null | Out-Null
        $sourceTracked = ($LASTEXITCODE -eq 0)
    }
    catch { $sourceTracked = $false }
    if ($sourceTracked) { $pathspec.Add($sourcePath) }
    if (Test-Path $destPath) { $pathspec.Add($destPath) }
    Write-Info "Archived $($matches_[0].Name)"
}

if (Test-Path $planPath) { $pathspec.Add($planPath) }

# Defence in depth: every path returned traces back to an id this call actually
# received, so a future edit that widens $pathspec by accident cannot hand the
# caller's git commit a stray path (the caller passes .Pathspec straight through).
foreach ($p in $pathspec) {
    if ($p -eq $planPath) { continue }
    $normalized = $p -replace '/', '\'
    if (-not $normalized.StartsWith($todosDir, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "archive-batch.ps1: refusing to return pathspec entry '$p' - not under '$todosDir' and not PLAN.md"
    }
    $leaf = Split-Path -Leaf $p
    if (-not (Test-FilenameInInput $leaf)) {
        throw "archive-batch.ps1: refusing to return pathspec entry '$p' - '$leaf' does not trace back to any input id"
    }
}

if ($failures.Count -gt 0) {
    foreach ($f in $failures) { Write-Warning "[$RepoRoot] $f" }
}

Write-Output ([PSCustomObject]@{
    Pathspec = $pathspec.ToArray()
    Failures = $failures.ToArray()
})

if ($failures.Count -gt 0) { exit 1 }
