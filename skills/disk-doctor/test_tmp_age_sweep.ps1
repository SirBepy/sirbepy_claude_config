<#
.SYNOPSIS
  Self-test for tmp-age-sweep.ps1, run via ci/run_all.py's skill-script discovery.

.DESCRIPTION
  Builds a fake C:\tmp under a temp dir and dot-sources the script's functions, so nothing under
  the real C:\tmp is ever read or touched. The one run against the real script file only passes a
  refused root. Exits 0 on pass, 1 on any failed assertion.

.PARAMETER Script
  Script under test; defaults to the sibling tmp-age-sweep.ps1. Lets a mutated scratch copy prove
  the assertions go red.
#>
param([string]$Script = (Join-Path $PSScriptRoot 'tmp-age-sweep.ps1'))
$ErrorActionPreference = 'Stop'

$failures = New-Object System.Collections.Generic.List[string]
function Assert($Condition, $Message) {
    if ($Condition) { Write-Host "  PASS: $Message" }
    else { $failures.Add($Message); Write-Host "  FAIL: $Message" }
}

. $Script

$fake = Join-Path ([System.IO.Path]::GetTempPath()) ('tmp-age-sweep-test-' + [guid]::NewGuid().ToString('N'))
$outside = Join-Path ([System.IO.Path]::GetTempPath()) ('tmp-age-sweep-outside-' + [guid]::NewGuid().ToString('N'))
$decoy = Join-Path ([System.IO.Path]::GetTempPath()) ('tmp-age-sweep-decoy-' + [guid]::NewGuid().ToString('N'))
$now = Get-Date
$old =$now.AddDays(-40)
$fresh = $now.AddDays(-2)

function New-Item2([string]$Path, [datetime]$When, [bool]$IsDir = $false) {
    if ($IsDir) { $null = New-Item -ItemType Directory -Path $Path -Force }
    else {
        $parent = Split-Path $Path -Parent
        if (-not (Test-Path $parent)) { $null = New-Item -ItemType Directory -Path $parent -Force }
        [System.IO.File]::WriteAllText($Path, 'x')
        (Get-Item -LiteralPath $Path).LastWriteTime = $When
    }
}
function Set-DirTime([string]$Path, [datetime]$When) { (Get-Item -LiteralPath $Path).LastWriteTime = $When }

try {
    $null = New-Item -ItemType Directory -Path $fake -Force
    $null = New-Item -ItemType Directory -Path $outside -Force
    New-Item2 (Join-Path $outside 'precious.txt') $old

    # old dir: every file old
    New-Item2 "$fake\old-dir\a.txt" $old
    New-Item2 "$fake\old-dir\sub\b.txt" $old
    # new dir
    New-Item2 "$fake\new-dir\a.txt" $fresh
    # old dir with one new nested file
    New-Item2 "$fake\mixed-dir\a.txt" $old
    New-Item2 "$fake\mixed-dir\deep\er\c.txt" $fresh
    # empty old dir
    $null = New-Item -ItemType Directory -Path "$fake\empty-old" -Force
    # old loose file
    New-Item2 "$fake\old-loose.log" $old
    # keep-list items, all old
    New-Item2 "$fake\salvage\x.txt" $old
    New-Item2 "$fake\memory-backup-2026\x.txt" $old
    New-Item2 "$fake\Plugin.java" $old
    New-Item2 "$fake\Plugin.java.bak" $old
    New-Item2 "$fake\sftp-keep\x.txt" $old
    New-Item2 "$fake\live-one.yml" $old
    New-Item2 "$fake\n8n-db.sqlite" $old
    New-Item2 "$fake\extra-keep\x.txt" $old
    # cc-target: 10 days idle is under its 21-day floor even with -Days 5; another at 40 days
    New-Item2 "$fake\cc-target\x.txt" $now.AddDays(-10)
    # old dir holding a junction to a tree outside the root
    New-Item2 "$fake\linky\a.txt" $old
    cmd /c mklink /J "$fake\linky\jn" "$outside" | Out-Null

    # Directory mtimes move on every child create, so pin them old last (except the fresh ones).
    foreach ($d in 'old-dir', 'old-dir\sub', 'mixed-dir', 'mixed-dir\deep', 'mixed-dir\deep\er', 'empty-old', 'salvage', 'memory-backup-2026', 'sftp-keep', 'extra-keep', 'linky') {
        Set-DirTime "$fake\$d" $old
    }
    Set-DirTime "$fake\cc-target" $now.AddDays(-10)
    Set-DirTime "$fake\new-dir" $fresh

    Write-Host '=== Get-TmpSweepPlan ==='
    $plan = Get-TmpSweepPlan -Root $fake -Days 21 -KeepList ($script:DefaultKeep + @('extra-keep'))
    $names = @($plan | ForEach-Object { $_.Name })

    Assert ($names -contains 'old-dir') 'old dir is listed'
    Assert ($names -contains 'old-loose.log') 'old loose file is listed'
    Assert ($names -contains 'empty-old') 'old empty dir is listed'
    Assert ($names -contains 'linky') 'old dir containing a junction is listed'
    Assert (-not ($names -contains 'new-dir')) 'new dir is never listed'
    Assert (-not ($names -contains 'mixed-dir')) 'old dir with one new nested file is never listed'
    foreach ($k in 'salvage', 'memory-backup-2026', 'Plugin.java', 'Plugin.java.bak', 'sftp-keep', 'live-one.yml', 'n8n-db.sqlite', 'extra-keep') {
        Assert (-not ($names -contains $k)) "keep-list item '$k' is never listed"
    }
    Assert (-not ($names -contains 'cc-target')) 'cc-target under 21 days is never listed'

    $short = Get-TmpSweepPlan -Root $fake -Days 5 -KeepList $script:DefaultKeep
    Assert (-not (@($short | ForEach-Object { $_.Name }) -contains 'cc-target')) 'cc-target keeps its 21-day floor even with -Days 5'

    $oldSize = ($plan | Where-Object Name -eq 'old-dir').Bytes
    Assert ($oldSize -eq 2) "old dir byte total counts both nested files (got $oldSize)"

    Write-Host '=== Assert-SweepRoot ==='
    Assert ((Assert-SweepRoot 'C:\tmp') -eq 'C:\tmp') 'C:\tmp accepted'
    Assert ((Assert-SweepRoot 'c:\TMP\') -eq 'C:\tmp') 'case and trailing slash normalised'
    Assert ($null -eq (Assert-SweepRoot 'C:\')) 'drive root refused'
    Assert ($null -eq (Assert-SweepRoot 'C:\tmp\sub')) 'a child of C:\tmp refused'
    Assert ($null -eq (Assert-SweepRoot 'C:\tmp\..\Windows')) 'dot-dot escape refused'
    Assert ($null -eq (Assert-SweepRoot $fake)) 'an arbitrary temp dir refused'

    Write-Host '=== script entrypoint ==='
    $psExe = (Get-Process -Id $PID).Path
    # The foreign root is a decoy temp dir, never a real system path: if the refusal ever
    # regressed, -Apply would delete only this decoy.
    New-Item2 "$decoy\old-item\a.txt" $old
    Set-DirTime "$decoy\old-item" $old
    & $psExe -NoProfile -ExecutionPolicy Bypass -File $Script -Root $decoy -Apply | Out-Null
    Assert ($LASTEXITCODE -eq 2) "foreign root exits 2 even with -Apply (got $LASTEXITCODE)"
    Assert (Test-Path "$decoy\old-item\a.txt") 'refused run left the foreign root alone'

    Write-Host '=== Invoke-TmpSweep preview ==='
    $null = Invoke-TmpSweep -Root $fake -Days 21 -KeepList ($script:DefaultKeep + @('extra-keep')) -Apply $false
    Assert (Test-Path "$fake\old-dir\a.txt") 'preview deletes nothing'
    Assert (Test-Path "$fake\old-loose.log") 'preview leaves the loose file'

    Write-Host '=== Invoke-TmpSweep -Apply ==='
    $null = Invoke-TmpSweep -Root $fake -Days 21 -KeepList ($script:DefaultKeep + @('extra-keep')) -Apply $true
    Assert (-not (Test-Path "$fake\old-dir")) 'apply removes the old dir'
    Assert (-not (Test-Path "$fake\old-loose.log")) 'apply removes the old loose file'
    Assert (-not (Test-Path "$fake\empty-old")) 'apply removes the old empty dir'
    Assert (-not (Test-Path "$fake\linky")) 'apply removes the dir holding the junction'
    Assert (Test-Path "$outside\precious.txt") 'junction target outside the root survives apply'
    Assert (Test-Path "$fake\new-dir\a.txt") 'apply keeps the new dir'
    Assert (Test-Path "$fake\mixed-dir\deep\er\c.txt") 'apply keeps the mixed dir'
    Assert (Test-Path "$fake\salvage\x.txt") 'apply keeps salvage'
    Assert (Test-Path "$fake\n8n-db.sqlite") 'apply keeps n8n-db.sqlite'
    Assert (Test-Path "$fake\cc-target\x.txt") 'apply keeps young cc-target'
}
finally {
    foreach ($p in $fake, $outside, $decoy) {
        if (Test-Path -LiteralPath $p) {
            try { Remove-TreeSafe $p } catch { Write-Host "cleanup of $p failed: $($_.Exception.Message)" }
        }
    }
}

if ($failures.Count -gt 0) {
    Write-Host "`n$($failures.Count) FAILED:"
    $failures | ForEach-Object { Write-Host "  - $_" }
    exit 1
}
Write-Host "`nAll passed."
exit 0
