<#
.SYNOPSIS
  Self-test for d-cargo-sweep.ps1's tier D selection (Get-TierDDeletions). Deletes nothing outside
  its own temp folder and never reads D:.

.DESCRIPTION
  Builds a fake debug\deps under a temp dir with files of chosen ages, runs the selection on the
  listing, and asserts which files it would delete. Exits 0 on pass, 1 on any failed assertion.

.PARAMETER Lib
  Selection library under test; defaults to the sibling d-cargo-sweep-lib.ps1. Lets a copy with the
  old keep rule prove the assertions go red.
#>
param([string]$Lib = (Join-Path $PSScriptRoot 'd-cargo-sweep-lib.ps1'))
$ErrorActionPreference = 'Stop'

$failures = New-Object System.Collections.Generic.List[string]
function Assert($Condition, $Message) {
  if ($Condition) { Write-Host "  PASS: $Message" }
  else { $failures.Add($Message); Write-Host "  FAIL: $Message" }
}

. $Lib

$deps = Join-Path ([System.IO.Path]::GetTempPath()) ('d-cargo-sweep-test-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $deps -Force
$now = Get-Date

function New-Dep([string]$Name, [double]$AgeDays) {
  $p = Join-Path $deps $Name
  [System.IO.File]::WriteAllText($p, 'x')
  (Get-Item -LiteralPath $p).LastWriteTime = $now.AddDays(-$AgeDays)
}

try {
  $own = New-Object System.Collections.Generic.HashSet[string]
  foreach ($n in 'lib_a', 'lib_b', 'lib_c', 'lib_d') { [void]$own.Add($n) }

  # lib_a: the newest hash is metadata-only (cargo check), the only runnable one is older than the cut.
  New-Dep 'lib_a-aaaaaaaaaaaaaaaa.d' 1
  foreach ($e in 'exe', 'pdb', 'd', 'o') { New-Dep "lib_a-bbbbbbbbbbbbbbbb.$e" 20 }
  foreach ($e in 'exe', 'pdb', 'd') { New-Dep "lib_a-cccccccccccccccc.$e" 40 }

  # lib_b: an ordinary crate, newest hash has binaries, two older variants.
  foreach ($e in 'exe', 'pdb', 'd') { New-Dep "lib_b-1111111111111111.$e" 1 }
  foreach ($e in 'exe', 'pdb', 'd') { New-Dep "lib_b-2222222222222222.$e" 30 }
  foreach ($e in 'exe', 'pdb', 'd', 'o') { New-Dep "lib_b-3333333333333333.$e" 40 }

  # lib_c: several metadata-only hashes and no binary anywhere: nothing runnable to protect, so the
  # rule is the plain "newest only" one.
  New-Dep 'lib_c-aaaaaaaaaaaaaaaa.d' 1
  New-Dep 'lib_c-bbbbbbbbbbbbbbbb.d' 30
  New-Dep 'lib_c-cccccccccccccccc.d' 40

  # lib_d: an old hash holding only object files sits behind the newest hash.
  foreach ($e in 'exe', 'd') { New-Dep "lib_d-aaaaaaaaaaaaaaaa.$e" 1 }
  New-Dep 'lib_d-dddddddddddddddd.o' 40

  # Not ours: untouched whatever its age.
  New-Dep 'serde-aaaaaaaaaaaaaaaa.d' 90
  New-Dep 'serde-bbbbbbbbbbbbbbbb.d' 91

  $listing = Get-ChildItem $deps -File
  $cut = $now.AddDays(-7)
  $del = @(Get-TierDDeletions -DepFiles $listing -Own $own -ObjCut $cut)
  $names = @($del | ForEach-Object { $_.Name })

  Write-Host 'metadata-only newest hash'
  foreach ($e in 'exe', 'pdb', 'd', 'o') { Assert ($names -notcontains "lib_a-bbbbbbbbbbbbbbbb.$e") "lib_a keeps the only runnable hash's .$e" }
  Assert ($names -notcontains 'lib_a-aaaaaaaaaaaaaaaa.d') 'lib_a keeps its newest (metadata-only) hash'
  foreach ($e in 'exe', 'pdb', 'd') { Assert ($names -contains "lib_a-cccccccccccccccc.$e") "lib_a lists the older binary hash's .$e for deletion" }

  Write-Host 'ordinary crate'
  foreach ($e in 'exe', 'pdb', 'd') { Assert ($names -notcontains "lib_b-1111111111111111.$e") "lib_b keeps the newest hash's .$e" }
  foreach ($e in 'exe', 'pdb', 'd') { Assert ($names -contains "lib_b-2222222222222222.$e") "lib_b lists the older variant's .$e" }
  foreach ($e in 'exe', 'pdb', 'd', 'o') { Assert ($names -contains "lib_b-3333333333333333.$e") "lib_b lists the oldest variant's .$e" }

  Write-Host 'crate with no binary at all'
  Assert ($names -notcontains 'lib_c-aaaaaaaaaaaaaaaa.d') 'lib_c keeps its newest hash'
  Assert (($names -contains 'lib_c-bbbbbbbbbbbbbbbb.d') -and ($names -contains 'lib_c-cccccccccccccccc.d')) 'lib_c lists the older metadata-only hashes'

  Write-Host 'object-only leftovers and other crates'
  Assert ($names -contains 'lib_d-dddddddddddddddd.o') 'lib_d lists an old object-only variant'
  Assert ($names -notcontains 'lib_d-aaaaaaaaaaaaaaaa.exe') 'lib_d keeps its newest hash'
  Assert (-not ($names | Where-Object { $_ -like 'serde-*' })) 'a crate that is not ours is never listed'

  Write-Host 'only listed names are files in debug\deps'
  Assert (-not ($del | Where-Object { $_.DirectoryName -ne $deps })) 'every listed file is inside the deps folder'
} finally {
  Remove-Item -LiteralPath $deps -Recurse -Force -ErrorAction SilentlyContinue
}

if ($failures.Count -gt 0) {
  Write-Host "`n$($failures.Count) assertion(s) failed"
  exit 1
}
Write-Host "`nall assertions passed"
exit 0
