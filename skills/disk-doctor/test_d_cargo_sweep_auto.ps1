<#
.SYNOPSIS
  Self-test for d-cargo-sweep-auto.ps1's log line and exit code. Deletes nothing.

.DESCRIPTION
  Runs the wrapper in a child process against a stub sweep script, on drive C: with a temp log dir,
  so no cargo-target directory is read or removed. The stub prints canned sweep output and exits with
  the code under test. Exits 0 on pass, 1 on any failed assertion.

.PARAMETER Script
  Wrapper under test; defaults to the sibling d-cargo-sweep-auto.ps1. Lets an older copy prove the
  assertions go red.
#>
param([string]$Script = (Join-Path $PSScriptRoot 'd-cargo-sweep-auto.ps1'))
$ErrorActionPreference = 'Stop'

$failures = New-Object System.Collections.Generic.List[string]
function Assert($Condition, $Message) {
  if ($Condition) { Write-Host "  PASS: $Message" }
  else { $failures.Add($Message); Write-Host "  FAIL: $Message" }
}

$work = Join-Path ([System.IO.Path]::GetTempPath()) ('d-cargo-sweep-auto-test-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $work -Force
$hostExe = (Get-Process -Id $PID).Path

function New-Stub([string]$Name, [string[]]$Lines, [int]$ExitCode) {
  $path = Join-Path $work "$Name-stub.ps1"
  $body = "param([switch]`$Apply, [string]`$Tiers)`r`n" + (($Lines | ForEach-Object { "Write-Output '$_'" }) -join "`r`n") + "`r`nexit $ExitCode`r`n"
  [System.IO.File]::WriteAllText($path, $body)
  return $path
}

# Runs the wrapper; ThresholdPct 101 means C: always counts as under the threshold. 'no-such-build'
# keeps a cargo process on this machine from turning the run into a skip.
function Invoke-Wrapper([string]$Name, [string]$Stub, [int]$Threshold = 101, [string[]]$Builds = @('no-such-build')) {
  $logDir = Join-Path $work "log-$Name"
  $null = & $hostExe -NoProfile -File $Script -ThresholdPct $Threshold -Drive C -SweepScript $Stub -LogDir $logDir -BuildProcesses $Builds 2>&1
  $log = Join-Path $logDir 'log.txt'
  [pscustomobject]@{ Exit = $LASTEXITCODE; Log = $(if (Test-Path $log) { [System.IO.File]::ReadAllText($log) } else { '' }) }
}

try {
  Write-Host 'sweep finished normally, with more removed lines than the old 12-line cap'
  $removed = 1..15 | ForEach-Object { "removed D:\cargo-target\debug\incremental\claude_conductor_lib-$_" }
  $r = Invoke-Wrapper 'ok' (New-Stub 'ok' ($removed + 'Tier D: removed 40 of 41 files (1 not removed: locked)') 0)
  Assert ($r.Exit -eq 0) "exit 0 propagates (got $($r.Exit))"
  Assert ($r.Log -match '\bdone: ') 'logs done'
  Assert ($r.Log -match '15 dirs removed') 'counts the removed dirs instead of listing them'
  Assert ($r.Log -match 'Tier D: removed 40 of 41') 'keeps the Tier D summary even after 15 removed lines'
  Assert ($r.Log -notmatch 'refused|aborted|failed') 'no failure word on a clean run'

  Write-Host 'sweep left many dirs behind (STILL PRESENT lines before the Tier D summary)'
  $stuck = 1..15 | ForEach-Object { "STILL PRESENT D:\cargo-target\debug\incremental\locked-$_" }
  $r = Invoke-Wrapper 'stuck' (New-Stub 'stuck' ($stuck + 'Tier D: removed 3 of 41 files (38 not removed: locked)') 0)
  Assert ($r.Log -match '15 still present') 'counts the STILL PRESENT dirs instead of listing them'
  Assert ($r.Log -match 'Tier D: removed 3 of 41') 'keeps the Tier D summary behind 15 STILL PRESENT lines'

  Write-Host 'child refused (exit 3)'
  $r = Invoke-Wrapper 'refused' (New-Stub 'refused' @('REFUSING -Apply: a build is running. Stop these first:') 3)
  Assert ($r.Exit -eq 3) "exit 3 propagates (got $($r.Exit))"
  Assert ($r.Log -match '\brefused \(exit 3') 'logs refused'
  Assert ($r.Log -notmatch '\bdone:') 'does not log done'
  Assert ($r.Log -match 'REFUSING') 'keeps the REFUSING line'

  Write-Host 'child aborted mid-sweep (exit 4)'
  $r = Invoke-Wrapper 'aborted' (New-Stub 'aborted' @('removed D:\cargo-target\debug\incremental\a-1', 'ABORT: a build started during the sweep, stopping so it keeps its files.') 4)
  Assert ($r.Exit -eq 4) "exit 4 propagates (got $($r.Exit))"
  Assert ($r.Log -match '\baborted \(exit 4') 'logs aborted'
  Assert ($r.Log -notmatch '\bdone:') 'does not log done'
  Assert ($r.Log -match 'ABORT') 'keeps the ABORT line'

  Write-Host 'child crashed (any other code)'
  $r = Invoke-Wrapper 'failed' (New-Stub 'failed' @('boom') 7)
  Assert ($r.Exit -eq 7) "exit 7 propagates (got $($r.Exit))"
  Assert ($r.Log -match '\bfailed \(exit 7') 'logs failed'

  Write-Host 'no-op paths'
  $r = Invoke-Wrapper 'noop' (New-Stub 'noop' @('SHOULD NOT RUN') 9) 0
  Assert ($r.Exit -eq 0 -and $r.Log -match '\bok: ') 'under no pressure: logs ok, exits 0, never calls the sweep'
  Assert ($r.Log -notmatch 'SHOULD NOT RUN|sweep:') 'the stub was not run'
  $r = Invoke-Wrapper 'busy' (New-Stub 'busy' @('SHOULD NOT RUN') 9) 101 @($hostExe | Split-Path -Leaf | ForEach-Object { [System.IO.Path]::GetFileNameWithoutExtension($_) })
  Assert ($r.Exit -eq 0 -and $r.Log -match '\bskip: ') 'a running build: logs skip, exits 0, never calls the sweep'
} finally {
  Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}

if ($failures.Count -gt 0) {
  Write-Host "`n$($failures.Count) assertion(s) failed"
  exit 1
}
Write-Host "`nall assertions passed"
exit 0
