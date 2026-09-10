<#
Emits a /mega-todos per-builder dispatch prompt. Reads the canonical preamble
from refs/builder-preamble.md and the injected commit block from this skill's
own SKILL.md - both stay the single source of truth on disk, this script only
fills the parts that vary per dispatch (todo 472).

Two output shapes, chosen by -Compact:

- Default (full): the entire resolved preamble + commit block text, inlined.
  Byte-exact, but ~12KB/dispatch that the orchestrator must hold in context
  twice (once reading this script's output, once retyping it into the Agent
  tool's `prompt` field) - see todo 949.
- -Compact: a short prompt (the three guard markers inlined verbatim, plus
  per-dispatch specifics) that points the BUILDER at the same two source
  files and tells it to read and follow them itself, with the placeholder
  substitutions spelled out. The builder pays one Read call in its own
  fresh context instead of the orchestrator paying two copies in the shared
  one. Proven against a real dispatch 2026-09-10 (todo 949).

-AsJsLiteral escapes the chosen output (backslash, backtick, `${`) for safe
embedding inside a JS template literal, e.g. a Workflow script's agent(`...`)
call. Combine with -Compact: escaping a ~12KB block by hand is exactly the
hazard todo 938 documents (backticks terminate the literal, `\t`/`\U` are
silently-consumed escapes); escaping the short compact form is a few dozen
bytes and mechanical. Do not use -AsJsLiteral alone on the full block for a
real dispatch - it technically works but produces an unreviewable wall of
escaped text; prefer -Compact -AsJsLiteral for any Workflow-authored run.
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
    [string] $Extra = '',
    [switch] $Compact,
    [switch] $AsJsLiteral
)

$ErrorActionPreference = 'Stop'

# An -Owned entry is a path, never prose. A space or a parenthesis is the
# signature of task description that leaked into the files list (observed
# 2026-09-05: '-Owned' entry read `templates/ (the entire tree, all files
# under it)` and got substituted verbatim into `git commit -- <FILES>`,
# producing a command that cannot run). Task description belongs in -Task.
foreach ($entry in $Owned) {
    if ($entry -match '[\s()]') {
        throw "-Owned entry '$entry' looks like prose, not a path (contains whitespace or a parenthesis). " +
              "Task description belongs in -Task; -Owned takes exact file paths only."
    }
}

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
# inventing a paraphrase (builder-preamble.md's own note on this case). This
# paragraph IS marker 1 (contains "Stage your changes but do NOT commit"),
# so both output shapes inline it verbatim rather than pointing at it.
$commitParas = $commitBlock -split "`n`n", 2
$stagingLine = $commitParas[0]
$commitRest = $commitParas[1]

# -replace's replacement side treats a bare `$` as a backreference token;
# escape it so a literal path or task string can't be misread as one.
function Protect([string]$Text) { $Text -replace '\$', '$$$$' }

$filesArg = ($Owned -join ' ')

# NewFiles only annotates the human-readable list; git commands above use
# $Owned's plain paths, since "(NEW)" in a pathspec would break the commit.
$ownedList = ($Owned | ForEach-Object {
    if ($NewFiles -contains $_) { "  $_ (NEW)" } else { "  $_" }
}) -join "`n"

if ($Compact) {
    $banInstruction = if ($inClaudeDir) {
        'GLOBAL_EDIT_BAN -> DELETE that line entirely; this working directory IS ~/.claude, so global work is the assigned task.'
    } else {
        'GLOBAL_EDIT_BAN -> keep the line exactly as printed in the file, do not delete it.'
    }

    $final = @"
Windows. PowerShell for shell commands. Working directory: $WorkingDir.

$stagingLine

Read $preamblePath in full now, before doing anything else, and follow its fenced code block as
your working preamble VERBATIM, applying these substitutions to its placeholders:
  WORKING_DIR -> $WorkingDir
  STAGING_LINE -> already given above (do not re-read that placeholder from the file)
  OFF_LIMITS -> $OffLimits
  $banInstruction

run_in_background is FORBIDDEN in builder subagents at every step of this dispatch, and so is
Monitor - the file you just read carries the full orphan-check and 120-second-timeout rules,
they apply exactly as written there.

If this dispatch captures screenshots, save them under .for_bepy/screenshots/<id>/ per the file
you just read.

## YOUR FILES - the only paths you may write

$ownedList

# YOUR TASK

$Task
"@

    if ($VerifyFloor) { $final += "`n`n## VERIFY FLOOR`n`n$VerifyFloor" }
    if ($Extra) { $final += "`n`n$Extra" }

    $final += @"


# COMMITTING IS PART OF YOUR JOB

Read the fenced code block under the heading "## The injected commit block" in $skillPath in full
and follow it VERBATIM, applying:
  EXPECTED_BRANCH -> $ExpectedBranch
  FILES -> $filesArg
  PREFIX: <title> -> $CommitMessage
"@
} else {
    $prompt = $preambleBlock `
        -replace '<WORKING_DIR>', (Protect $WorkingDir) `
        -replace '<STAGING_LINE>', (Protect $stagingLine) `
        -replace '<OFF_LIMITS>', (Protect $OffLimits)

    if ($inClaudeDir) {
        $prompt = ($prompt -split "`n") | Where-Object { $_ -ne '<GLOBAL_EDIT_BAN>' } | Out-String
    } else {
        $prompt = $prompt -replace '<GLOBAL_EDIT_BAN>', (Protect $banCell)
    }

    $commitRest = $commitRest -replace '<EXPECTED_BRANCH>', (Protect $ExpectedBranch)
    $commitRest = $commitRest -replace '<FILES>', (Protect $filesArg)
    $commitRest = $commitRest -replace '<PREFIX>: <title>', (Protect $CommitMessage)

    $sections = @($prompt.Trim())
    $sections += "## YOUR FILES - the only paths you may write`n`n$ownedList"
    $sections += "# YOUR TASK`n`n$Task"
    if ($VerifyFloor) { $sections += "## VERIFY FLOOR`n`n$VerifyFloor" }
    if ($Extra) { $sections += $Extra }
    $sections += "# COMMITTING IS PART OF YOUR JOB`n`n$commitRest"

    $final = ($sections -join "`n`n")
}

# The three literal markers hooks/dispatch-preamble-guard.py checks must
# survive emission - assert here rather than trust the substitutions above.
$missing = @()
if ($final -notmatch [regex]::Escape('Stage your changes but do NOT commit') -and $final -notmatch [regex]::Escape('Leave all changes unstaged')) {
    $missing += 'staging line'
}
if ($final -notmatch 'run_in_background' -or $final -notmatch 'FORBIDDEN') { $missing += 'run_in_background/FORBIDDEN' }
if ($final -notmatch [regex]::Escape('.for_bepy/screenshots/') -and $final -notmatch 'READ-ONLY DISPATCH') { $missing += 'screenshot-id marker' }
if ($missing.Count -gt 0) { throw "Emitted prompt is missing required marker(s): $($missing -join ', ')" }

if ($AsJsLiteral) {
    # Order matters: double existing backslashes first, THEN escape backtick
    # and `${` - otherwise the backslash this step adds would itself get
    # doubled by the next replace. -replace's replacement side is a LITERAL
    # string (single-quoted, no PowerShell escaping, and .NET Regex.Replace
    # gives backslash no special meaning there) - '\\' is already 2 chars,
    # not 1, so this produces one extra backslash per original, i.e. doubled.
    $final = $final -replace '\\', '\\'
    $final = $final -replace '`', '\`'
    $final = $final -replace '\$\{', '\${'
}

$final
