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

-CommitMode selects which commit procedure the builder's prompt carries
(todo 974). Default 'PerBuilder' reproduces every existing caller's output
byte-for-byte: the builder commits its own work via the injected commit
block, unchanged. 'Barrier' is SKILL.md's "Barrier COMMIT_MODE" - the
builder never touches git; it runs only step 2 (diff review) and step 3
(the prefilter) of the same injected block as its verify floor, then reports
finished paths, and the main thread commits by pathspec at the next barrier.
Steps 2 and 3 are extracted verbatim from the same on-disk commit block
(never a hand-copied duplicate), so a future edit to those steps' wording
stays the single source of truth. See SKILL.md's own note that in `barrier`
mode <STAGING_LINE>'s "Leave all changes unstaged..." variant is simply true
(the builder genuinely never commits), unlike `per-builder` mode where the
same line would be a lie the injected block immediately overrides.

-NoCommitBlock (todo 1028) is the generalization: any orchestrator other
than /mega-todos itself - /loop-todos, /auto-do-todos, an ad-hoc dispatch -
gets a compliant preamble-based prompt from -Owned/-OffLimits/-Task alone,
with no -CommitMessage/-ExpectedBranch and no read of
skills/mega-todos/SKILL.md at all. Chosen over teaching -CommitMode a third
value, because "no commit block" is not a third commit PROCEDURE, it is the
absence of one - conflating it with PerBuilder/Barrier would make a generic
caller pick between two mega-todos-specific git procedures it has no use
for. The staging line then falls back to the doctrine's plain default
(refs/builder-preamble.md's own two <STAGING_LINE> variants); -SharedIndex
picks the "leave unstaged" one for a repo sharing a git index with
concurrent sessions, the same condition that file's placeholder table
documents.
#>
param(
    [Parameter(Mandatory)] [string[]] $Owned,
    [Parameter(Mandatory)] [string] $OffLimits,
    [Parameter(Mandatory)] [string] $Task,
    [string] $CommitMessage = '',
    [string] $ExpectedBranch = '',
    [string] $WorkingDir = (Get-Location).Path,
    [string[]] $NewFiles = @(),
    [string] $VerifyFloor = '',
    [string] $Extra = '',
    [switch] $Compact,
    [switch] $AsJsLiteral,
    [switch] $NoCommitBlock,
    [switch] $SharedIndex,
    [ValidateSet('PerBuilder', 'Barrier')] [string] $CommitMode = 'PerBuilder'
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

# A generic caller passing -NoCommitBlock never commits via mega-todos' own
# procedure, so -CommitMessage/-ExpectedBranch have nothing to fill - only
# require them for the one mode that still substitutes them into the
# injected block.
if (-not $NoCommitBlock -and $CommitMode -eq 'PerBuilder' -and (-not $CommitMessage -or -not $ExpectedBranch)) {
    throw "-CommitMessage and -ExpectedBranch are required unless -NoCommitBlock is set (todo 1028: " +
          "a dispatch that never commits its own work passes -NoCommitBlock instead of a commit message/branch)."
}

$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$preamblePath = Join-Path $repoRoot 'refs\builder-preamble.md'

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

# -replace's replacement side treats a bare `$` as a backreference token;
# escape it so a literal path or task string can't be misread as one.
function Protect([string]$Text) { $Text -replace '\$', '$$$$' }

$filesArg = ($Owned -join ' ')

# NewFiles only annotates the human-readable list; git commands above use
# $Owned's plain paths, since "(NEW)" in a pathspec would break the commit.
$ownedList = ($Owned | ForEach-Object {
    if ($NewFiles -contains $_) { "  $_ (NEW)" } else { "  $_" }
}) -join "`n"

if ($NoCommitBlock) {
    # Todo 1028: a caller outside /mega-todos has no injected commit block to
    # borrow a staging line from, so it gets the doctrine's plain default -
    # the same two <STAGING_LINE> variants refs/builder-preamble.md's own
    # placeholder table documents, chosen by -SharedIndex.
    $stagingLine = if ($SharedIndex) {
        'Leave all changes unstaged. The main agent will run /commit by pathspec after your report-back.'
    } else {
        'Stage your changes but do NOT commit. The main agent will run /commit after your report-back.'
    }
} else {
    $skillPath = Join-Path $repoRoot 'skills\mega-todos\SKILL.md'
    $skillLines = Get-Content -Path $skillPath
    $commitBlock = Get-FirstFencedBlock -Lines $skillLines -SourcePath $skillPath

    # Per-builder mode can't use <STAGING_LINE> truthfully since the builder
    # commits - fill it with the commit block's own opening sentence instead
    # of inventing a paraphrase (builder-preamble.md's own note on this
    # case). This paragraph IS marker 1 (contains "Stage your changes but do
    # NOT commit"), so both output shapes inline it verbatim rather than
    # pointing at it.
    $commitParas = $commitBlock -split "`n`n", 2
    $stagingLine = $commitParas[0]
    $commitRest = $commitParas[1]

    # Barrier mode overrides the staging line with the placeholder table's
    # other <STAGING_LINE> variant (refs/builder-preamble.md) - truthful here
    # since a barrier builder genuinely never touches git - and needs steps
    # 2 and 3 pulled out of the same on-disk commit block, verbatim, never
    # re-typed.
    if ($CommitMode -eq 'Barrier') {
        $stagingLine = 'Leave all changes unstaged. The main agent will run /commit by pathspec after your report-back.'

        $barrierStepsPattern = '(?ms)^2\.\s.*?(?=^4\.\s)'
        $barrierStepsMatch = [regex]::Match($commitRest, $barrierStepsPattern)
        if (-not $barrierStepsMatch.Success) { throw "Could not extract steps 2-3 from the commit block in $skillPath" }
        $barrierSteps = $barrierStepsMatch.Value.TrimEnd() -replace '<FILES>', (Protect $filesArg)
    }
}

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

    if (-not $NoCommitBlock) {
        if ($CommitMode -eq 'Barrier') {
            $final += @"


# YOUR VERIFY FLOOR - COMMIT_MODE IS BARRIER, YOU DO NOT COMMIT

Read the fenced code block under the heading "## The injected commit block" in $skillPath, then
read the "### Barrier COMMIT_MODE" section immediately after it in the same file - it is what
tells you which of that block's steps are yours. Per that section: follow ONLY step 2 (diff
review) and step 3 (the prefilter, carve-out included) as your verify floor, applying:
  FILES -> $filesArg

Do NOT run steps 1, 4, 5, or 6 of that block: no commit marker, no `git add`, no branch guard, no
`git commit`. Report your finished paths in your report-back without touching git further; the
main thread commits them by pathspec at the next barrier.
"@
        } else {
            $final += @"


# COMMITTING IS PART OF YOUR JOB

Read the fenced code block under the heading "## The injected commit block" in $skillPath in full
and follow it VERBATIM, applying:
  EXPECTED_BRANCH -> $ExpectedBranch
  FILES -> $filesArg
  PREFIX: <title> -> $CommitMessage
"@
        }
    }
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

    $sections = @($prompt.Trim())
    $sections += "## YOUR FILES - the only paths you may write`n`n$ownedList"
    $sections += "# YOUR TASK`n`n$Task"
    if ($VerifyFloor) { $sections += "## VERIFY FLOOR`n`n$VerifyFloor" }
    if ($Extra) { $sections += $Extra }

    if (-not $NoCommitBlock) {
        if ($CommitMode -eq 'Barrier') {
            $barrierSection = @"
# YOUR VERIFY FLOOR - COMMIT_MODE IS BARRIER, YOU DO NOT COMMIT

This run's COMMIT_MODE is barrier. Per the "### Barrier COMMIT_MODE" section of ${skillPath}: you
never run steps 1, 4, 5, or 6 of the injected commit block below - only step 2 (diff review) and
step 3 (the prefilter, carve-out included), as your verify floor. Then report your finished paths
without touching git further; the main thread commits them by pathspec at the next barrier.

$barrierSteps
"@
            $sections += $barrierSection
        } else {
            $commitRest = $commitRest -replace '<EXPECTED_BRANCH>', (Protect $ExpectedBranch)
            $commitRest = $commitRest -replace '<FILES>', (Protect $filesArg)
            $commitRest = $commitRest -replace '<PREFIX>: <title>', (Protect $CommitMessage)
            $sections += "# COMMITTING IS PART OF YOUR JOB`n`n$commitRest"
        }
    }

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
