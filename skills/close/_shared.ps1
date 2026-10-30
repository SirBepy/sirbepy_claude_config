# Dot-sourced by claim-todo.ps1, complete-todo.ps1, reserve-todo-id.ps1
# and mega-todos/archive-batch.ps1. Not a module - these
# scripts are invoked directly by path, matching this tree's convention.
#
# The single place that knows the todo id shape: "<label>-<NNNN>" (device label, then a
# number zero-padded to 4 digits on write, any padding accepted on read), e.g. pc-1407.
# hooks/_todo_ids.py is the Python twin of this file; the two must stay in step. No other
# script may carry its own id regex.

# Every todo made before device labels existed was made on this PC, so a bare-numeric
# filename ("1407-slug.md", "07-x.md") reads as this label regardless of which machine
# is reading it.
$script:LegacyTodoLabel = 'pc'
$script:DeviceLabelRegex = '^[a-z]+[0-9]*$'

# CLAUDE_DEVICE_LABEL_FILE exists so tests point at a temp label file and never read or
# write the real ~/.claude/device-label.
function Get-DeviceLabelPath {
    if ($env:CLAUDE_DEVICE_LABEL_FILE) { return $env:CLAUDE_DEVICE_LABEL_FILE }
    return (Join-Path $HOME '.claude\device-label')
}

# Throws (never defaults) when the file is missing or malformed: a second machine that
# silently defaulted to "pc" would mint ids that collide with this one's.
function Get-DeviceLabel {
    $path = Get-DeviceLabelPath
    $fix = 'Set the label: write "pc" or "mac" (pc2/mac2 for a second one) to ~/.claude/device-label'
    if (-not (Test-Path -LiteralPath $path)) {
        throw "No device label found at '$path'. $fix"
    }
    $raw = [System.IO.File]::ReadAllText($path).Trim([char]0xFEFF, ' ', "`t", "`r", "`n")
    if ($raw -cnotmatch $script:DeviceLabelRegex) {
        throw "Invalid device label '$raw' in '$path' (must match $($script:DeviceLabelRegex)). $fix"
    }
    return $raw
}

function Format-TodoId {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][int64]$Number
    )
    return ('{0}-{1:D4}' -f $Label.ToLowerInvariant(), $Number)
}

# Parses a typed id: "1407", "pc-1407", "pc-7", or either with a "-<slug>" tail. Label is
# $null for a bare number. Returns $null when the text is not an id at all (a prefix-less
# malformed stem).
function Parse-TodoId {
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return $null }
    $m = [regex]::Match($Text.Trim(), '^(?:(?<label>[a-z]+[0-9]*)-)?(?<num>[0-9]{1,15})(?:-(?<slug>.*))?$', 'IgnoreCase')
    if (-not $m.Success) { return $null }
    $label = $null
    if ($m.Groups['label'].Success) { $label = $m.Groups['label'].Value.ToLowerInvariant() }
    $slug = $null
    if ($m.Groups['slug'].Success -and $m.Groups['slug'].Value -ne '') { $slug = $m.Groups['slug'].Value }
    return [pscustomobject]@{
        Label  = $label
        Number = [int64]$m.Groups['num'].Value
        Slug   = $slug
    }
}

# Parses a backlog/done "*.md", a ".claims" "*.claim" or a "*-.reserved" marker NAME.
# A legacy bare-numeric name reads as the legacy label. A backlog .md must carry a slug
# (that is what separates a todo file from some other note that merely ends in digits).
function Get-TodoNameInfo {
    param([string]$Name)
    $stem = $null
    $needSlug = $false
    if ($Name -match '^(.+)\.md$') { $stem = $matches[1]; $needSlug = $true }
    elseif ($Name -match '^(.+)\.claim$') { $stem = $matches[1] }
    elseif ($Name -match '^(.+)\.reserved$') { $stem = $matches[1] }
    if ($null -eq $stem) { return $null }
    $parsed = Parse-TodoId $stem
    if ($null -eq $parsed) { return $null }
    if ($needSlug -and -not $parsed.Slug) { return $null }
    $legacy = ($null -eq $parsed.Label)
    $label = if ($legacy) { $script:LegacyTodoLabel } else { $parsed.Label }
    return [pscustomobject]@{
        Label  = $label
        Number = $parsed.Number
        Slug   = $parsed.Slug
        Legacy = $legacy
    }
}

# Items = FileInfo objects. Keeps those whose name carries (Label, Number) and, when -Slug is
# given, that slug.
function Select-TodoNameMatches {
    param(
        $Items,
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][int64]$Number,
        [string]$Slug
    )
    $out = @()
    foreach ($item in @($Items)) {
        $info = Get-TodoNameInfo $item.Name
        if ($null -eq $info) { continue }
        if ($info.Label -ne $Label -or $info.Number -ne $Number) { continue }
        if ($Slug -and $info.Slug -ne $Slug) { continue }
        $out += $item
    }
    return $out
}

# Resolves a typed id (or full "<id>-<slug>" stem) to backlog files in $Dir.
#
# A bare number resolves to THIS device's label first; failing that, a unique match on
# another label; several labels matching is an error naming every candidate. A text that
# is not an id at all falls back to an exact "<stem>.md" match (a prefix-less filename:
# malformed per ai-todos-format.md but still archivable).
#
# Returns Id (canonical "pc-1407", or the stem for a fallback), Label, Number, Slug,
# Matches (slug-filtered), SiblingCount (matches before the slug filter), FellBack, and
# Error (non-null = could not resolve; callers report it, Matches is empty).
function Resolve-TodoFile {
    param(
        [Parameter(Mandatory = $true)][string]$Dir,
        [Parameter(Mandatory = $true)][string]$RawId,
        [string]$Slug
    )

    $result = [ordered]@{
        Id           = $RawId
        Label        = $null
        Number       = $null
        Slug         = $Slug
        Matches      = @()
        SiblingCount = 0
        FellBack     = $false
        Error        = $null
    }
    $allFiles = @(Get-ChildItem -Path $Dir -Filter '*.md' -File -ErrorAction SilentlyContinue)

    $parsed = Parse-TodoId $RawId
    if ($null -eq $parsed) {
        $stemMatches = @($allFiles | Where-Object { $_.Name -ieq "$RawId.md" })
        if ($stemMatches.Count -gt 0) {
            $result.Matches = $stemMatches
            $result.SiblingCount = $stemMatches.Count
            $result.Slug = $null
            $result.FellBack = $true
        }
        return $result
    }

    if (-not $Slug) { $Slug = $parsed.Slug }
    $result.Slug = $Slug
    $number = $parsed.Number
    $label = $parsed.Label

    if (-not $label) {
        $device = Get-DeviceLabel
        $labelsWithNumber = @()
        foreach ($f in $allFiles) {
            $info = Get-TodoNameInfo $f.Name
            if ($info -and $info.Number -eq $number -and $labelsWithNumber -notcontains $info.Label) {
                $labelsWithNumber += $info.Label
            }
        }
        if ($labelsWithNumber -contains $device) { $label = $device }
        elseif ($labelsWithNumber.Count -eq 1) { $label = $labelsWithNumber[0] }
        elseif ($labelsWithNumber.Count -gt 1) {
            $candidates = ($labelsWithNumber | Sort-Object | ForEach-Object { Format-TodoId $_ $number }) -join ', '
            $result.Error = "Ambiguous id '$RawId': it exists on several devices ($candidates) and none is this device ('$device'). Retry with the full id, e.g. $(Format-TodoId $labelsWithNumber[0] $number)."
            return $result
        }
        else { $label = $device }
    }

    $result.Label = $label
    $result.Number = $number
    $result.Id = Format-TodoId $label $number
    $sameId = @(Select-TodoNameMatches -Items $allFiles -Label $label -Number $number)
    $result.SiblingCount = $sameId.Count
    if ($Slug) { $sameId = @(Select-TodoNameMatches -Items $sameId -Label $label -Number $number -Slug $Slug) }
    $result.Matches = $sameId
    return $result
}

# Regex FRAGMENT matching how a PLAN.md line spells an id: the label-prefixed form with any
# zero padding, plus - for the legacy label only - the bare number older lines carry.
function Get-TodoPlanIdPattern {
    param(
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][int64]$Number
    )
    $lab = [regex]::Escape($Label)
    if ($Label -eq $script:LegacyTodoLabel) { return "(?:$lab-)?0*$Number" }
    return "$lab-0*$Number"
}

# Claim files in $ClaimsDir for (Label, Number). With -Slug: the slug-suffixed claim; else
# the plain claim; else a lone slug-suffixed one (claim-todo.ps1 names it that way when the
# id collides, so a sibling task's claim survives).
function Find-TodoClaims {
    param(
        [Parameter(Mandatory = $true)][string]$ClaimsDir,
        [Parameter(Mandatory = $true)][string]$Label,
        [Parameter(Mandatory = $true)][int64]$Number,
        [string]$Slug
    )
    if (-not (Test-Path $ClaimsDir)) { return @() }
    $claims = @(Get-ChildItem -Path $ClaimsDir -Filter '*.claim' -File -ErrorAction SilentlyContinue)
    $forId = @(Select-TodoNameMatches -Items $claims -Label $Label -Number $Number)
    $found = @()
    if ($Slug) { $found = @($forId | Where-Object { (Get-TodoNameInfo $_.Name).Slug -eq $Slug }) }
    if ($found.Count -eq 0) { $found = @($forId | Where-Object { -not (Get-TodoNameInfo $_.Name).Slug }) }
    if ($found.Count -eq 0) {
        $slugged = @($forId | Where-Object { (Get-TodoNameInfo $_.Name).Slug })
        if ($slugged.Count -eq 1) { $found = $slugged }
    }
    return $found
}
