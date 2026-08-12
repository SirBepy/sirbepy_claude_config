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
$MarkerRe = '(?m)^<!--[ \t]*cleanup:.*?-->[ \t]*\r?\n?'
$ClaimRe  = '(?m)^<!--[ \t]*Claim before executing:.*?-->[ \t]*\r?\n'
$TitleRe  = '(?m)^#[ \t]'

# A real marker lives in the header, above the title. Todos that DOCUMENT the marker format quote
# it in their prose, and an unanchored search treats that quote as the marker (2026-08-12: todo 99's
# evidence block was overwritten this way).
function Get-HeaderMarker {
    param([string]$Text)
    $title = [regex]::Match($Text, $TitleRe)
    $limit = if ($title.Success) { $title.Index } else { $Text.Length }
    $m = [regex]::Match($Text, $MarkerRe)
    if ($m.Success -and $m.Index -lt $limit) { return $m }
    return $null
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
  $existing = Get-HeaderMarker -Text $text

  $oldHash = $null; $oldCount = 0
  if ($existing) {
    $h = [regex]::Match($existing.Value, 'content-hash=([0-9a-f]+)')
    $c = [regex]::Match($existing.Value, 'reconfirm-count=(\d+)')
    if ($h.Success) { $oldHash = $h.Groups[1].Value }
    if ($c.Success) { $oldCount = [int]$c.Groups[1].Value }
  }

  $valid = $row.still_valid -eq 'true'
  if (-not $valid)                             { $count = [Math]::Max($oldCount, 1) }
  elseif ($existing -and $oldHash -eq $newHash) { $count = $oldCount + 1 }
  else                                         { $count = 1 }

  $marker = "<!-- cleanup: last-checked $Date, complexity=$($row.complexity), worth=$($row.worth), reconfirm-count=$count, content-hash=$newHash -->"

  if ($existing) {
    # Splice by index. String.Replace swaps EVERY occurrence, so a prose copy of the marker
    # elsewhere in the file would be rewritten too.
    $trailer = if ($existing.Value -match '\r?\n$') { [regex]::Match($existing.Value, '\r?\n$').Value } else { "`r`n" }
    $updated = $text.Substring(0, $existing.Index) + $marker + $trailer + $text.Substring($existing.Index + $existing.Length)
  } else {
    $claim = [regex]::Match($text, $ClaimRe)
    if ($claim.Success) {
      $at = $claim.Index + $claim.Length
      $updated = $text.Substring(0, $at) + $marker + "`r`n" + $text.Substring($at)
    } else {
      $updated = $marker + "`r`n" + $text
    }
  }

  if ($updated -eq $text) { $skipped++; continue }

  if ($PSCmdlet.ShouldProcess($row.file, 'update cleanup marker')) {
    [System.IO.File]::WriteAllText($path, $updated, (New-Object System.Text.UTF8Encoding($false)))
    $written++
  }
  $report += [pscustomobject]@{ file = $row.file; worth = $row.worth; count = $count; hash = $newHash; had_marker = [bool]$existing }
}

# Emit objects, not a formatted table - Format-Table here breaks any caller that pipes this.
$report
"written=$written skipped=$skipped total=$($rows.Count)"
