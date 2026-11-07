# Selection logic for d-cargo-sweep.ps1, in its own file so test_d_cargo_sweep.ps1 can dot-source it
# without running a sweep.

# Tier D: the files of superseded variants of our own crates in debug\deps.
# $DepFiles is the Get-ChildItem listing of debug\deps, $Own the crate names that are ours, $ObjCut
# the age line (a variant whose newest artifact is newer than it is always kept).
# Per crate, two variants are kept whatever their age: the newest overall, and the newest one that
# carries an .exe or .pdb. A metadata-only build (cargo check) writes just <crate>-<hash>.d, so
# without the second rule it would become "the newest" and the only runnable test binary, sitting
# one rank below it, would be deleted.
function Get-TierDDeletions {
  param($DepFiles, [System.Collections.Generic.HashSet[string]]$Own, [datetime]$ObjCut)
  # Group by crate + 16-hex hash. A hash's age is its newest NON-.o file, so a variant that was just
  # linked is never mistaken for an old one because of stale object files.
  $units = @{}
  foreach ($f in $DepFiles) {
    if ($f.Name -notmatch '^(?<crate>[A-Za-z0-9_]+)-(?<hash>[0-9a-f]{16})\.(?<rest>.+)$') { continue }
    if (-not $Own.Contains($Matches['crate'])) { continue }
    $k = $Matches['crate'] + '-' + $Matches['hash']
    if (-not $units.ContainsKey($k)) {
      $units[$k] = [PSCustomObject]@{ Crate = $Matches['crate']; Newest = [datetime]::MinValue; HasBinary = $false; Files = (New-Object System.Collections.ArrayList) }
    }
    [void]$units[$k].Files.Add($f)
    if ($f.Name -notlike '*.o' -and $f.LastWriteTime -gt $units[$k].Newest) { $units[$k].Newest = $f.LastWriteTime }
    if ($f.Name -match '\.(exe|pdb)$') { $units[$k].HasBinary = $true }
  }
  $del = New-Object System.Collections.ArrayList
  foreach ($grp in ($units.Values | Group-Object Crate)) {
    $sorted = @($grp.Group | Sort-Object Newest -Descending)
    $newestBinary = $sorted | Where-Object { $_.HasBinary } | Select-Object -First 1
    for ($i = 1; $i -lt $sorted.Count; $i++) {   # index 0 is the newest variant: always kept
      if ($sorted[$i].Newest -ge $ObjCut) { continue }
      if ($sorted[$i] -eq $newestBinary) { continue }
      foreach ($f in $sorted[$i].Files) {
        if ($f.Name -match '\.(pdb|exe|d|o)$') { [void]$del.Add($f) }
      }
    }
  }
  return @($del)
}
