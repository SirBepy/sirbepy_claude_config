<#
.SYNOPSIS
  Writes or refreshes the `<!-- cleanup: ... -->` marker on todo files from a verdict table.

.DESCRIPTION
  Step 5 of /cleanup-todos. Replacement is a literal String.Replace, never [regex]::Replace -
  a `$` inside a todo's prose is a substitution token to the latter and silently eats text.

.EXAMPLE
  .\update-markers.ps1 -TodosDir C:\repo\.claude\todos -DataFile .\verdicts.csv -Date 2026-08-12 -WhatIf
#>
[CmdletBinding(SupportsShouldProcess)]
param(
  [Parameter(Mandatory)][string]$TodosDir,
  [Parameter(Mandatory)][string]$DataFile,
  [Parameter(Mandatory)][ValidatePattern('^\d{4}-\d{2}-\d{2}$')][string]$Date
)

$ErrorActionPreference = 'Stop'
$MarkerRe   = '(?m)^<!--[ \t]*cleanup:.*?-->[ \t]*\r?\n?'
$ClaimRe    = '(?m)^<!--[ \t]*Claim before executing:.*?-->[ \t]*\r?\n'
$TitleRe    = '(?m)^#[ \t]'
$SectionRe  = '(?m)^##[ \t]'

# A real marker lives in the header, either above the title or between the title and the first
# `## ` section. Todos that DOCUMENT the marker format quote it in prose inside a `##` section, and
# an unanchored search treats that quote as the marker (2026-08-12: todo 99's evidence block was
# overwritten this way) - the section boundary is what still excludes that case.
function Get-HeaderMarkers {
    param([string]$Text)
    $title   = [regex]::Match($Text, $TitleRe)
    $section = [regex]::Match($Text, $SectionRe)
    $limit   = if ($section.Success) { $section.Index } else { $Text.Length }
    $above = $null; $below = $null
    foreach ($m in [regex]::Matches($Text, $MarkerRe)) {
        if ($m.Index -ge $limit) { continue }
        if ($title.Success -and $m.Index -ge $title.Index) {
            if (-not $below) { $below = $m }
        } else {
            $above = $m
        }
    }
    [pscustomobject]@{ Above = $above; Below = $below }
}

function Get-MarkerFields {
    param($Match)
    if (-not $Match) { return $null }
    $h = [regex]::Match($Match.Value, 'content-hash=([0-9a-f]+)')
    $c = [regex]::Match($Match.Value, 'reconfirm-count=(\d+)')
    $d = [regex]::Match($Match.Value, 'last-checked[ \t]+(\d{4}-\d{2}-\d{2})')
    [pscustomobject]@{
        Hash  = if ($h.Success) { $h.Groups[1].Value } else { $null }
        Count = if ($c.Success) { [int]$c.Groups[1].Value } else { 0 }
        Date  = if ($d.Success) { $d.Groups[1].Value } else { $null }
    }
}

# Files in this backlog are LF or CRLF depending on how they were last written; matching that on
# insert is what keeps a one-line fix from turning into a whole-file diff (todo 449).
function Get-LineEnding {
    param([string]$Text)
    if ($Text -match "`r`n") { return "`r`n" }
    return "`n"
}

function Get-SectionHash {
  param([string]$Text)
  # Hash Goal + Approach only, so an unrelated Notes edit does not reset reconfirm-count.
  $parts = @()
  foreach ($h in @('Goal', 'Approach')) {
    $m = [regex]::Match($Text, "(?ms)^##[ \t]+$h[ \t]*\r?\n(.*?)(?=^##[ \t]|\z)")
    if ($m.Success) { $parts += $m.Groups[1].Value.Trim() }
  }
  $joined = ($parts -join "`n") -replace "`r`n", "`n"
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    $bytes = $sha.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($joined))
  } finally { $sha.Dispose() }
  (($bytes | ForEach-Object { $_.ToString('x2') }) -join '').Substring(0, 8)
}

$rows = Import-Csv -Path $DataFile
$written = 0; $skipped = 0; $report = @()

foreach ($row in $rows) {
  $path = Join-Path $TodosDir $row.file
  if (-not (Test-Path -LiteralPath $path)) {
    Write-Warning "missing: $($row.file)"; $skipped++; continue
  }

  $text     = [System.IO.File]::ReadAllText($path)
  $newHash  = Get-SectionHash -Text $text
  $eol      = Get-LineEnding -Text $text
  $markers  = Get-HeaderMarkers -Text $text
  $above    = Get-MarkerFields -Match $markers.Above
  $below    = Get-MarkerFields -Match $markers.Below

  # A below-title marker is always dropped; the write lands above the title either way. When both
  # exist the baseline is whichever is chronologically older, since that is the genuine prior check -
  # the below one is normally the original and the above one a prior buggy run's stray duplicate,
  # but an explicit date beats that assumption.
  $existing = $markers.Above
  $toDelete = $null
  if ($markers.Above -and $markers.Below) {
    $toDelete = $markers.Below
    $baseline = if ($above.Date -and $below.Date -and $above.Date -lt $below.Date) { $above } else { $below }
  } elseif ($markers.Above) {
    $baseline = $above
  } elseif ($markers.Below) {
    $toDelete = $markers.Below
    $baseline = $below
  } else {
    $baseline = $null
  }
  $oldHash  = if ($baseline) { $baseline.Hash } else { $null }
  $oldCount = if ($baseline) { $baseline.Count } else { 0 }

  $valid = $row.still_valid -eq 'true'
  if (-not $valid)                             { $count = [Math]::Max($oldCount, 1) }
  elseif ($baseline -and $oldHash -eq $newHash)  { $count = $oldCount + 1 }
  else                                         { $count = 1 }

  $marker = "<!-- cleanup: last-checked $Date, complexity=$($row.complexity), worth=$($row.worth), reconfirm-count=$count, content-hash=$newHash -->"

  # Any below-title marker is cut first, so the write below always leaves exactly one marker above
  # the title - the state Step 5's gate requires. Indices before the cut are unshifted, so
  # $existing stays valid against $body.
  $body = $text
  if ($toDelete) {
    $body = $text.Substring(0, $toDelete.Index) + $text.Substring($toDelete.Index + $toDelete.Length)
  }

  if ($existing) {
    # Splice by index. String.Replace swaps EVERY occurrence, so a prose copy of the marker
    # elsewhere in the file would be rewritten too.
    $trailer = if ($existing.Value -match '\r?\n$') { [regex]::Match($existing.Value, '\r?\n$').Value } else { $eol }
    $updated = $body.Substring(0, $existing.Index) + $marker + $trailer + $body.Substring($existing.Index + $existing.Length)
  } else {
    $claim = [regex]::Match($body, $ClaimRe)
    if ($claim.Success) {
      $at = $claim.Index + $claim.Length
      $updated = $body.Substring(0, $at) + $marker + $eol + $body.Substring($at)
    } else {
      $updated = $marker + $eol + $body
    }
  }

  if ($updated -eq $text) { $skipped++; continue }

  if ($PSCmdlet.ShouldProcess($row.file, 'update cleanup marker')) {
    [System.IO.File]::WriteAllText($path, $updated, (New-Object System.Text.UTF8Encoding($false)))
    $written++
  }
  $report += [pscustomobject]@{ file = $row.file; worth = $row.worth; count = $count; hash = $newHash; had_marker = [bool]($existing -or $toDelete) }
}

# Emit objects, not a formatted table - Format-Table here breaks any caller that pipes this.
$report
"written=$written skipped=$skipped total=$($rows.Count)"
