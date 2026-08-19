<#
.SYNOPSIS
  Orphan-process forensics audit (Windows). Advise-only - never kills anything.
.DESCRIPTION
  Answers "what is eating my RAM / did we leak processes" in one call instead of four
  hand-written PowerShell blocks:
    - top consumers grouped by process name, summed working set
    - chromium-family window count vs process count (process count alone is misleading -
      many processes with one window is normal multi-process architecture, not a leak)
    - rootless processes: parent-dead and pid-recycled reported SEPARATELY
    - ancestry chains for a named scope back to a live owner process (default: claude)
  Matches /disk-doctor's posture: prints findings and the exact kill command, never kills.
.PARAMETER NameFilter
  Optional process-name substring (e.g. 'node', 'brave') to scope the ancestry-chain section.
.PARAMETER Top
  How many rows to show in the top-consumers table. Default 15.
.PARAMETER OwnerProcessName
  Process name to walk ancestry chains up to. Default 'claude'.
.EXAMPLE
  ./orphan-audit.ps1
.EXAMPLE
  ./orphan-audit.ps1 -NameFilter node -Top 20
#>

param(
    [string]$NameFilter,
    [int]$Top = 15,
    [string]$OwnerProcessName = 'claude'
)

$ErrorActionPreference = 'Stop'

Write-Host "=== Orphan Process Audit (advise-only, never kills) ===" -ForegroundColor Cyan

# One CIM snapshot reused throughout: has CreationDate + ParentProcessId + WorkingSetSize,
# which Get-Process alone does not expose together.
$all = Get-CimInstance Win32_Process
$byPid = @{}
foreach ($p in $all) { $byPid[[int]$p.ProcessId] = $p }

# ---------- 1. Top consumers by summed working set ----------
Write-Host "`n--- Top $Top consumers (summed working set) ---" -ForegroundColor Yellow
$all |
    Group-Object Name |
    ForEach-Object {
        [PSCustomObject]@{
            Name    = $_.Name
            Count   = $_.Count
            TotalMB = [math]::Round((($_.Group | Measure-Object WorkingSetSize -Sum).Sum) / 1MB, 1)
        }
    } |
    Sort-Object TotalMB -Descending |
    Select-Object -First $Top |
    Format-Table -AutoSize

# ---------- 2. Chromium-family: window count vs process count ----------
Write-Host "`n--- Chromium-family: window count vs process count ---" -ForegroundColor Yellow
$chromiumNames = $all.Name | Where-Object { $_ -match '(?i)brave|chrome|msedge|electron|webview2' } | Select-Object -Unique
if ($chromiumNames) {
    $(foreach ($name in $chromiumNames) {
        $procCount = ($all | Where-Object Name -eq $name).Count
        $winCount = (Get-Process -Name ($name -replace '\.exe$', '') -ErrorAction SilentlyContinue |
            Where-Object { $_.MainWindowTitle -ne '' }).Count
        [PSCustomObject]@{
            Name         = $name
            ProcessCount = $procCount
            WindowCount  = $winCount
        }
    }) | Format-Table -AutoSize
    Write-Host "Process count is not window count - a large count with few windows is normal Chromium multi-process architecture." -ForegroundColor DarkGray
} else {
    Write-Host "(none found)"
}

# ---------- 3. Rootless processes: parent-dead vs pid-recycled ----------
Write-Host "`n--- Rootless processes ---" -ForegroundColor Yellow
$parentDead = @()
$pidRecycled = @()
foreach ($p in $all) {
    $ppid = [int]$p.ParentProcessId
    if ($ppid -eq 0) { continue }
    $parent = $byPid[$ppid]
    if (-not $parent) {
        $parentDead += $p
    } elseif ($parent.CreationDate -and $p.CreationDate -and $parent.CreationDate -gt $p.CreationDate) {
        # parent PID now belongs to a process created AFTER the child - PID was reused, not a real orphan
        $pidRecycled += $p
    }
}

Write-Host "Parent-dead ($($parentDead.Count)):" -ForegroundColor DarkYellow
if ($parentDead.Count -gt 0) {
    $parentDead | Select-Object ProcessId, Name, ParentProcessId, CreationDate | Format-Table -AutoSize
} else { Write-Host "  (none)" }

Write-Host "PID-recycled - parent PID reused by a newer process ($($pidRecycled.Count)):" -ForegroundColor DarkYellow
if ($pidRecycled.Count -gt 0) {
    $pidRecycled | Select-Object ProcessId, Name, ParentProcessId, CreationDate | Format-Table -AutoSize
} else { Write-Host "  (none)" }

# ---------- 4. Ancestry chains for a named scope back to a live owner ----------
if ($NameFilter) {
    Write-Host "`n--- Ancestry chains for '$NameFilter' back to a live '$OwnerProcessName' ---" -ForegroundColor Yellow
    $scoped = $all | Where-Object { $_.Name -match [regex]::Escape($NameFilter) }
    if (-not $scoped) {
        Write-Host "  (no processes match '$NameFilter')"
    }
    foreach ($p in $scoped) {
        $chain = New-Object System.Collections.Generic.List[string]
        $current = $p
        $seen = @{}
        $foundOwner = $false
        while ($current) {
            $chain.Add("$($current.Name)($($current.ProcessId))")
            if ($current.Name -match [regex]::Escape($OwnerProcessName)) { $foundOwner = $true; break }
            $ppid = [int]$current.ParentProcessId
            if ($seen.ContainsKey($ppid)) { break }
            $seen[$ppid] = $true
            $current = $byPid[$ppid]
        }
        $status = if ($foundOwner) { "OK - reaches $OwnerProcessName" } else { "ORPHAN - no live $OwnerProcessName in chain" }
        Write-Host "  $($chain -join ' <- ')  [$status]"
    }
} else {
    Write-Host "`n(pass -NameFilter <name> to see ancestry chains for a specific process family)" -ForegroundColor DarkGray
}

# ---------- Suggested cleanup, printed only, never executed ----------
if ($parentDead.Count -gt 0 -or $pidRecycled.Count -gt 0) {
    Write-Host "`n--- Suggested (not run) ---" -ForegroundColor Yellow
    foreach ($p in ($parentDead + $pidRecycled)) {
        Write-Host "  Stop-Process -Id $($p.ProcessId) -Force  # $($p.Name), parent $($p.ParentProcessId)"
    }
}

Write-Host "`nAdvise-only: nothing above was killed. Review before running any Stop-Process." -ForegroundColor Cyan
