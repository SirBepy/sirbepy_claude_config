<#
Emits a full /mega-todos per-builder dispatch prompt. Reads the canonical
preamble from refs/builder-preamble.md and the injected commit block from
this skill's own SKILL.md - both stay the single source of truth on disk,
this script only fills the parts that vary per dispatch (todo 472).
#>
param(
    [Parameter(Mandatory)] [string[]] $Owned,
    [Parameter(Mandatory)] [string] $OffLimits,
    [Parameter(Mandatory)] [string] $Task,
    [Parameter(Mandatory)] [string] $CommitMessage,
    [Parameter(Mandatory)] [string] $ExpectedBranch,
    [string] $WorkingDir = (Get-Location).Path,
    [string[]] $NewFiles = @(),
    [string] $VerifyFloor = '',
    [string] $Extra = ''
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$preamblePath = Join-Path $repoRoot 'refs\builder-preamble.md'
$skillPath = Join-Path $repoRoot 'skills\mega-todos\SKILL.md'

# A fenced block is delimited by two lines that are exactly ``` - both source
# files carry exactly one, so the first pair is the whole block.
function Get-FirstFencedBlock([string[]]$Lines, [string]$SourcePath) {
    $start = -1; $end = -1
    for ($i = 0; $i -lt $Lines.Count; $i++) {
        if ($Lines[$i].TrimEnd() -eq '```') {
            if ($start -eq -1) { $start = $i } else { $end = $i; break }
        }
    }
    if ($start -eq -1 -or $end -eq -1) { throw "No fenced code block found in $SourcePath" }
    return ($Lines[($start + 1)..($end - 1)] -join "`n")
}

$preambleLines = Get-Content -Path $preamblePath
$preambleBlock = Get-FirstFencedBlock -Lines $preambleLines -SourcePath $preamblePath

$skillLines = Get-Content -Path $skillPath
$commitBlock = Get-FirstFencedBlock -Lines $skillLines -SourcePath $skillPath

# The GLOBAL_EDIT_BAN substitute text lives only in the placeholder table,
# not the fenced block - read it from there instead of hardcoding a copy.
$banRow = $preambleLines | Where-Object { $_ -match '^\|\s*`<GLOBAL_EDIT_BAN>`' } | Select-Object -First 1
if (-not $banRow) { throw "GLOBAL_EDIT_BAN row not found in $preamblePath" }
$banCell = ($banRow -split '\|')[2].Trim()
if ($banCell.StartsWith('`') -and $banCell.EndsWith('`')) { $banCell = $banCell.Substring(1, $banCell.Length - 2) }
$banCell = $banCell -replace '\\`', '`'

# In ~/.claude sessions global work IS the task, so the ban is deleted per
# the table's own "Delete entirely when" column - never a placeholder-shaped gap.
$normalizedWorkingDir = $WorkingDir.TrimEnd('\', '/')
$normalizedRepoRoot = $repoRoot.TrimEnd('\', '/')
$inClaudeDir = $normalizedWorkingDir -ieq $normalizedRepoRoot

# Per-builder mode can't use <STAGING_LINE> truthfully since the builder
# commits - fill it with the commit block's own opening sentence instead of
# inventing a paraphrase (builder-preamble.md's own note on this case).
$commitParas = $commitBlock -split "`n`n", 2
$stagingLine = $commitParas[0]
$commitRest = $commitParas[1]

# -replace's replacement side treats a bare `$` as a backreference token;
# escape it so a literal path or task string can't be misread as one.
function Protect([string]$Text) { $Text -replace '\$', '$$$$' }

$prompt = $preambleBlock `
    -replace '<WORKING_DIR>', (Protect $WorkingDir) `
    -replace '<STAGING_LINE>', (Protect $stagingLine) `
    -replace '<OFF_LIMITS>', (Protect $OffLimits)

if ($inClaudeDir) {
    $prompt = ($prompt -split "`n") | Where-Object { $_ -ne '<GLOBAL_EDIT_BAN>' } | Out-String
} else {
    $prompt = $prompt -replace '<GLOBAL_EDIT_BAN>', (Protect $banCell)
}

$filesArg = ($Owned -join ' ')
$commitRest = $commitRest -replace '<EXPECTED_BRANCH>', (Protect $ExpectedBranch)
$commitRest = $commitRest -replace '<FILES>', (Protect $filesArg)
$commitRest = $commitRest -replace '<PREFIX>: <title>', (Protect $CommitMessage)

# NewFiles only annotates the human-readable list; git commands above use
# $Owned's plain paths, since "(NEW)" in a pathspec would break the commit.
$ownedList = ($Owned | ForEach-Object {
    if ($NewFiles -contains $_) { "  $_ (NEW)" } else { "  $_" }
}) -join "`n"

$sections = @($prompt.Trim())
$sections += "## YOUR FILES - the only paths you may write`n`n$ownedList"
$sections += "# YOUR TASK`n`n$Task"
if ($VerifyFloor) { $sections += "## VERIFY FLOOR`n`n$VerifyFloor" }
if ($Extra) { $sections += $Extra }
$sections += "# COMMITTING IS PART OF YOUR JOB`n`n$commitRest"

$final = ($sections -join "`n`n")

# The three literal markers hooks/dispatch-preamble-guard.py checks must
# survive emission - assert here rather than trust the substitutions above.
$missing = @()
if ($final -notmatch [regex]::Escape('Stage your changes but do NOT commit') -and $final -notmatch [regex]::Escape('Leave all changes unstaged')) {
    $missing += 'staging line'
}
if ($final -notmatch 'run_in_background' -or $final -notmatch 'FORBIDDEN') { $missing += 'run_in_background/FORBIDDEN' }
if ($final -notmatch [regex]::Escape('.for_bepy/screenshots/') -and $final -notmatch 'READ-ONLY DISPATCH') { $missing += 'screenshot-id marker' }
if ($missing.Count -gt 0) { throw "Emitted prompt is missing required marker(s): $($missing -join ', ')" }

$final
