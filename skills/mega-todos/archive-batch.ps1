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
  is a two-path change" and the /commit step 8 coverage check it traces to. Only paths that
  still exist on disk are emitted, so an untracked source (moved and gone, no delete to
  stage) never aborts the caller's git add the way it did for todo 848.

  Never commits. Prints the pathspec (plus PLAN.md, which complete-todo.ps1 prunes on every
  call) so the caller's own /commit runs its real gates - prefilter, branch guard, the
  Staged-pathspec coverage check - unchanged.

.PARAMETER Items
  One or more "<id>|<note>" pairs, e.g. "286|fixed the off-by-one". The note half is
  optional - "286" alone completes with no Notes bullet appended.

.PARAMETER RepoRoot
  Project root containing .claude/todos/. Passed through to complete-todo.ps1 unchanged;
  defaults the same way it does (git toplevel, else cwd).

.OUTPUTS
  A PSCustomObject with Pathspec (string[], existing paths only) and Failures (string[],
  one line per id that could not be resolved or archived) written to the success stream.
  Exits 1 if any item failed, so the caller cannot mistake a partial batch for a clean one.

.EXAMPLE
  $result = & ~/.claude/skills/mega-todos/archive-batch.ps1 -Items "286|fixed the bug","97|done"
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

# Mirrors Resolve-TodoFile's numericId normalization (strip a leading-zero run before
# the hyphen) so a filename prefix and an -Items entry compare equal either way.
function Get-NormalizedTodoId([string]$RawId) {
    if ($RawId -match '^0*(\d+)-(.+)$') { return $matches[1] }
    return $RawId
}

# Prefix-less stems (Resolve-TodoFile's fallback path) have no "<id>-" to strip,
# so the whole stem IS the id for matching purposes.
function Get-FilenameIdPrefix([string]$Name) {
    if ($Name -match '^0*(\d+)-') { return $matches[1] }
    return [System.IO.Path]::GetFileNameWithoutExtension($Name)
}

$pathspec = New-Object System.Collections.Generic.List[string]
$failures = New-Object System.Collections.Generic.List[string]
$inputIds = New-Object System.Collections.Generic.HashSet[string]

foreach ($item in $Items) {
    $parts = $item -split '\|', 2
    $id = $parts[0].Trim()
    $note = if ($parts.Count -gt 1) { $parts[1].Trim() } else { $null }
    [void]$inputIds.Add((Get-NormalizedTodoId $id))

    # Resolve against the LIVE backlog only, before archiving moves the file -
    # done/ is never globbed here, which is the bug this script exists to kill.
    $resolved = Resolve-TodoFile -Dir $todosDir -RawId $id
    $matches_ = $resolved.Matches
    # Resolve-TodoFile extracts a slug from a full "<id>-<slug>" stem but does not
    # itself filter by it (complete-todo.ps1 does this filter inline; mirrored here
    # so a stem passed as -Id can disambiguate a live-backlog id collision too).
    if ($matches_ -and @($matches_).Count -gt 1 -and $resolved.Slug) {
        $slugPattern = "^0*$([regex]::Escape($resolved.NumericId))-$([regex]::Escape($resolved.Slug))\.md$"
        $matches_ = $matches_ | Where-Object { $_.Name -match $slugPattern }
    }
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

    if (Test-Path $sourcePath) { $pathspec.Add($sourcePath) }
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
    $prefix = Get-FilenameIdPrefix (Split-Path -Leaf $p)
    if (-not $inputIds.Contains($prefix)) {
        throw "archive-batch.ps1: refusing to return pathspec entry '$p' - id prefix '$prefix' was not in the input id set"
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
