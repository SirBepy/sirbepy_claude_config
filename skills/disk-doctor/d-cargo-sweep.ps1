# d-cargo-sweep.ps1 - reclaim stale Rust build output on D: (the HDD that holds every CARGO_TARGET_DIR).
#
# Default is a PREVIEW: it lists what each tier would delete and deletes nothing. Add -Apply to delete.
# Claude never runs -Apply: the Claude Code harness refuses Remove-Item/rd on drive-root paths, so Joe runs it.
# Run it with every cargo/rustc build and every Claude session that builds Rust stopped; it refuses -Apply
# while cargo, rustc, rust-lld or link is running.
#
# Tiers (pick with -Tiers, default A,B,C,D,E). Apply order is A, B, E, C, D: incremental dirs go before
# deps objects because hardlinks between the two pin the same disk blocks until BOTH names are gone.
#   A  whole dirs under D:\cargo-target and D:\cargo-target-* whose newest file is older than -Days
#      (dead projects and scratch profiles). A dir with ANY file newer than -Days is skipped.
#   B  per-hash incremental dirs of -Crate under D:\cargo-target\debug\incremental. Keeps the newest
#      -KeepIncremental dirs and anything touched within -MinAgeDays; the rest is removed.
#      Incremental dirs are pure cache: the cost is a slower next incremental build, nothing else.
#   C  debug\deps\*.rcgu.o older than -ObjDays (default 7). Codegen-unit object files that cargo does
#      not track in .fingerprint; rustc regenerates them from the incremental cache. Rebuild cost only.
#   D  superseded variants of OUR OWN test/lib binaries in debug\deps: for each crate named in
#      claude_usage_in_taskbar\src-tauri\tests\*.rs (plus the four conductor crates), every
#      <crate>-<hash>.{pdb,exe,d,o} whose hash is not the newest for that crate and whose newest
#      artifact is older than -ObjDays. .rlib/.rmeta/.lib/.dll are never touched. Rebuild cost only.
#   E  D:\cargo-target\loop1025-target, a finished one-off Claude Conductor build from 2026-10-25
#      with no references, process or schedule (checked 2026-11-04). Skipped if touched within 7 days.
#
# Usage:
#   powershell -NoProfile -File C:\Users\tecno\.claude\skills\disk-doctor\d-cargo-sweep.ps1            (preview)
#   powershell -NoProfile -File C:\Users\tecno\.claude\skills\disk-doctor\d-cargo-sweep.ps1 -Apply     (delete)
#   add -Tiers A,B to run only some tiers.
#
# Sizes in the preview are apparent sizes (file length, or robocopy for dirs), which count a hardlinked
# file once per link, so they overstate what is freed. A 2026-11-04 inode scan put real freed space at
# about 125 GB for tier C and 119 GB for tier D, with 40 GB of overlap between them.
param(
  [switch]$Apply,
  [string[]]$Tiers = @('A', 'B', 'C', 'D', 'E'),
  [int]$Days = 21,
  [int]$ObjDays = 7,
  [int]$KeepIncremental = 5,
  [int]$MinAgeDays = 3,
  [string]$Crate = 'claude_conductor_lib'
)

$ErrorActionPreference = 'Continue'
# powershell -File hands "-Tiers B,C,D" over as one string, so split it back into tiers.
$Tiers = @($Tiers | ForEach-Object { $_ -split '[,\s]+' } | Where-Object { $_ })
$root = 'D:\cargo-target'
$deps = Join-Path $root 'debug\deps'
$testsDir = 'C:\Users\tecno\Desktop\Projects\claude_usage_in_taskbar\src-tauri\tests'

# Names are exact so a typo cannot widen the sweep; the globs cover the Chrome scratch profiles.
$tierAExact = @(
  'pomodoro-overlay__src-tauri', 'sirbepy_tauri_kit', 'server_supervisor__vendor__tauri_kit',
  'pomodoro-overlay__vendor__tauri_kit', 'mc-e2e-b7db', 'x86_64-pc-windows-msvc', 'bedrock-test-srv',
  'webview2_probe', 'geyser-enchant-srv', 'geyser-jars', 'hoard-shot-profile'
)
$tierAGlobs = @('cdp-prof-*', 'chrome-shot-prof*')
$tierASiblings = @('D:\cargo-target-926', 'D:\cargo-target-adt', 'D:\cargo-target-cctest')

function Get-DirGB($p) {
  $o = robocopy $p NULL /L /S /NJH /NFL /NDL /BYTES /XJ /R:0 /W:0
  $l = @($o | Where-Object { $_ -match '^\s*Bytes :' })[0]
  if ($l -and $l -match 'Bytes :\s+(\d+)') { [math]::Round([int64]$Matches[1] / 1GB, 2) } else { 0 }
}

# robocopy /MAXAGE:n skips files older than n days, so any file it lists is newer than n days.
function Has-RecentFile($p, $days) {
  $o = robocopy $p NULL /L /S /NJH /NJS /NDL /XJ /R:0 /W:0 /MAXAGE:$days
  return (@($o | Where-Object { $_ -match '\S' }).Count -gt 0)
}

function Get-NewestTime($p) {
  $m = Get-ChildItem $p -Recurse -File -Force -ErrorAction SilentlyContinue |
    Measure-Object LastWriteTime -Maximum
  if ($m.Maximum) { $m.Maximum } else { (Get-Item $p -Force).LastWriteTime }
}

if ($Apply) {
  $busy = Get-Process cargo, rustc, rust-lld, link -ErrorAction SilentlyContinue
  if ($busy) {
    Write-Host 'REFUSING -Apply: a build is running. Stop these first:' -ForegroundColor Red
    $busy | Select-Object Name, Id | Format-Table | Out-String | Write-Host
    exit 3
  }
}

$dirPlan = New-Object System.Collections.ArrayList     # whole directories (tiers A, B, E)
$filePlan = New-Object System.Collections.ArrayList    # one entry per file tier: Tier, Files, GB

if ($Tiers -contains 'A') {
  $cands = New-Object System.Collections.ArrayList
  foreach ($s in $tierASiblings) { if (Test-Path $s) { [void]$cands.Add($s) } }
  foreach ($n in $tierAExact) { $p = Join-Path $root $n; if (Test-Path $p) { [void]$cands.Add($p) } }
  foreach ($g in $tierAGlobs) {
    Get-ChildItem $root -Directory -Filter $g -Force -ErrorAction SilentlyContinue |
      ForEach-Object { [void]$cands.Add($_.FullName) }
  }
  foreach ($p in $cands) {
    if (Has-RecentFile $p $Days) {
      Write-Host ("A skip (touched within {0} days): {1}" -f $Days, $p) -ForegroundColor Yellow
    } else {
      [void]$dirPlan.Add([PSCustomObject]@{ Tier = 'A'; Path = $p; GB = (Get-DirGB $p) })
    }
  }
}

if ($Tiers -contains 'B') {
  $inc = Join-Path $root 'debug\incremental'
  if (Test-Path $inc) {
    $dirs = Get-ChildItem $inc -Directory -Filter "$Crate-*" -Force -ErrorAction SilentlyContinue |
      ForEach-Object { [PSCustomObject]@{ Path = $_.FullName; Newest = (Get-NewestTime $_.FullName) } } |
      Sort-Object Newest -Descending
    $cut = (Get-Date).AddDays(-$MinAgeDays)
    $i = 0
    foreach ($d in $dirs) {
      $i++
      if ($i -le $KeepIncremental -or $d.Newest -gt $cut) { continue }
      [void]$dirPlan.Add([PSCustomObject]@{ Tier = 'B'; Path = $d.Path; GB = (Get-DirGB $d.Path) })
    }
    Write-Host ("B: {0} incremental dirs for {1}, keeping newest {2} and anything newer than {3} days" -f $dirs.Count, $Crate, $KeepIncremental, $MinAgeDays)
  }
}

if ($Tiers -contains 'E') {
  $p = Join-Path $root 'loop1025-target'
  if (Test-Path $p) {
    if (Has-RecentFile $p 7) {
      Write-Host "E skip (touched within 7 days): $p" -ForegroundColor Yellow
    } else {
      [void]$dirPlan.Add([PSCustomObject]@{ Tier = 'E'; Path = $p; GB = (Get-DirGB $p) })
    }
  }
}

$depFiles = $null
if (($Tiers -contains 'C' -or $Tiers -contains 'D') -and (Test-Path $deps)) {
  Write-Host 'Listing debug\deps (about 80k files on an HDD, takes a few minutes)...'
  $depFiles = Get-ChildItem $deps -File -Force -ErrorAction SilentlyContinue
}

$objCut = (Get-Date).AddDays(-$ObjDays)

if ($Tiers -contains 'C' -and $depFiles) {
  $sel = @($depFiles | Where-Object { $_.Name -like '*.rcgu.o' -and $_.LastWriteTime -lt $objCut })
  [void]$filePlan.Add([PSCustomObject]@{
    Tier = 'C'; Files = @($sel | ForEach-Object { $_.FullName }); Count = $sel.Count
    GB = [math]::Round((($sel | Measure-Object Length -Sum).Sum) / 1GB, 2) })
}

if ($Tiers -contains 'D' -and $depFiles) {
  $own = New-Object System.Collections.Generic.HashSet[string]
  if (Test-Path $testsDir) {
    Get-ChildItem $testsDir -Filter *.rs -File | ForEach-Object { [void]$own.Add($_.BaseName) }
  }
  foreach ($n in @('claude_conductor_lib', 'cc_conductor_daemon', 'claude_conductor', 'conductor_mobile_lib')) { [void]$own.Add($n) }
  # Group by crate + 16-hex hash. A hash's age is its newest NON-.o file, so a variant that was just
  # linked is never mistaken for an old one because of stale object files.
  $units = @{}
  foreach ($f in $depFiles) {
    if ($f.Name -notmatch '^(?<crate>[A-Za-z0-9_]+)-(?<hash>[0-9a-f]{16})\.(?<rest>.+)$') { continue }
    if (-not $own.Contains($Matches['crate'])) { continue }
    $k = $Matches['crate'] + '-' + $Matches['hash']
    if (-not $units.ContainsKey($k)) {
      $units[$k] = [PSCustomObject]@{ Crate = $Matches['crate']; Newest = [datetime]::MinValue; Files = (New-Object System.Collections.ArrayList) }
    }
    [void]$units[$k].Files.Add($f)
    if ($f.Name -notlike '*.o' -and $f.LastWriteTime -gt $units[$k].Newest) { $units[$k].Newest = $f.LastWriteTime }
  }
  $del = New-Object System.Collections.ArrayList
  foreach ($grp in ($units.Values | Group-Object Crate)) {
    $sorted = @($grp.Group | Sort-Object Newest -Descending)
    for ($i = 1; $i -lt $sorted.Count; $i++) {   # index 0 is the newest variant: always kept
      if ($sorted[$i].Newest -ge $objCut) { continue }
      foreach ($f in $sorted[$i].Files) {
        if ($f.Name -match '\.(pdb|exe|d|o)$') { [void]$del.Add($f) }
      }
    }
  }
  [void]$filePlan.Add([PSCustomObject]@{
    Tier = 'D'; Files = @($del | ForEach-Object { $_.FullName }); Count = $del.Count
    GB = [math]::Round((($del | Measure-Object Length -Sum).Sum) / 1GB, 2) })
}

Write-Host ''
if ($dirPlan.Count -gt 0) {
  $dirPlan | Format-Table Tier, GB, Path -AutoSize | Out-String -Width 200 | Write-Host
}
$filePlan | Format-Table Tier, Count, GB -AutoSize | Out-String -Width 200 | Write-Host
$total = ($dirPlan | Measure-Object GB -Sum).Sum + ($filePlan | Measure-Object GB -Sum).Sum
Write-Host ("Total (apparent sizes, hardlinks overstate; tiers C and D overlap by about 40 GB): {0} GB" -f [math]::Round($total, 2))

if (-not $Apply) {
  Write-Host 'PREVIEW only, nothing deleted. Re-run with -Apply to delete.' -ForegroundColor Cyan
  exit 0
}

$free0 = [math]::Round((Get-Volume D).SizeRemaining / 1GB, 2)

foreach ($t in @('A', 'B', 'E')) {
  foreach ($item in ($dirPlan | Where-Object { $_.Tier -eq $t })) {
    # Only paths under the cargo-target trees, never anything else on D:.
    if ($item.Path -notmatch '^D:\\cargo-target(-[A-Za-z0-9]+)?(\\|$)') {
      Write-Host "Skipping out-of-scope path: $($item.Path)" -ForegroundColor Red
      continue
    }
    cmd /c rd /s /q "`"$($item.Path)`""
    $gone = -not (Test-Path $item.Path)
    Write-Host ("{0} {1}" -f $(if ($gone) { 'removed' } else { 'STILL PRESENT' }), $item.Path)
  }
}

foreach ($t in @('C', 'D')) {
  $set = $filePlan | Where-Object { $_.Tier -eq $t }
  if (-not $set) { continue }
  $ok = 0; $fail = 0
  foreach ($path in $set.Files) {
    if (-not $path.StartsWith($deps + '\')) { $fail++; continue }   # never leave debug\deps
    try { [System.IO.File]::Delete($path); if (-not (Test-Path -LiteralPath $path)) { $ok++ } else { $fail++ } }
    catch { $fail++ }
  }
  Write-Host ("Tier {0}: removed {1} of {2} files ({3} not removed: locked, already gone, or hardlink partner)" -f $t, $ok, $set.Count, $fail)
}

$free1 = [math]::Round((Get-Volume D).SizeRemaining / 1GB, 2)
Write-Host ("D: free {0} GB -> {1} GB" -f $free0, $free1)
