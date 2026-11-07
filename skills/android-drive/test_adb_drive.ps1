<#
.SYNOPSIS
  Self-test for adb-drive.ps1 against a stubbed `adb`; no device or emulator is touched.

.DESCRIPTION
  Defines a PowerShell function named `adb` in this scope. A script run with `&` resolves
  commands through its callers, so adb-drive.ps1's `& adb ...` lands on the stub. The stub logs
  every call and serves canned `devices`, `wm size` and `pull` results. Exits 0 on pass, 1 on
  any failed assertion.

.PARAMETER Script
  Script under test; defaults to the sibling adb-drive.ps1. Lets a mutated or older copy prove
  the assertions go red.
#>
param([string]$Script = (Join-Path $PSScriptRoot 'adb-drive.ps1'))
$ErrorActionPreference = 'Stop'

$failures = New-Object System.Collections.Generic.List[string]
function Assert($Condition, $Message) {
    if ($Condition) { Write-Host "  PASS: $Message" }
    else { $failures.Add($Message); Write-Host "  FAIL: $Message" }
}

Add-Type -AssemblyName System.Drawing
$work = Join-Path ([System.IO.Path]::GetTempPath()) ('adb-drive-test-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $work -Force

# A real 4x8 PNG, since the script reads its size back through System.Drawing.
$goodPng = Join-Path $work 'good.png'
$bmp = New-Object System.Drawing.Bitmap 4, 8
$bmp.Save($goodPng, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
$goodBytes = [System.IO.File]::ReadAllBytes($goodPng)

$global:AdbLog = New-Object System.Collections.Generic.List[string]
$global:DeviceLines = @("List of devices attached", "emulator-5554`tdevice")
$global:PullBytes = $goodBytes

# The stub mimics a real device's filesystem for the one temp file: screencap creates it, rm
# removes it, so an assertion can ask whether anything is left behind.
$global:DeviceFiles = New-Object System.Collections.Generic.HashSet[string]

function adb {
    $line = $args -join ' '
    $global:AdbLog.Add($line)
    if ($line -eq 'devices') { return $global:DeviceLines }
    if ($line -match 'shell wm size') { return 'Physical size: 4x8' }
    if ($line -match 'shell screencap -p (\S+)') { $null = $global:DeviceFiles.Add($Matches[1]); return }
    if ($line -match 'shell rm (\S+)') { $null = $global:DeviceFiles.Remove($Matches[1]); return }
    if ($line -match ' pull (\S+) (.+)$') {
        [System.IO.File]::WriteAllBytes($Matches[2], [byte[]]$global:PullBytes)
        return "$($Matches[1]): 1 file pulled"
    }
}

function Invoke-Drive([string]$Action, [hashtable]$Params = @{}) {
    $global:AdbLog.Clear()
    try {
        $out = & $Script $Action @Params
        return [pscustomobject]@{ Out = ($out -join "`n"); Error = $null }
    } catch {
        return [pscustomobject]@{ Out = ''; Error = $_.Exception.Message }
    }
}

try {
    Write-Host '1311: serial resolution'
    $global:DeviceLines = @("List of devices attached", "emulator-5554`tdevice")
    $r = Invoke-Drive 'dismiss-keyboard'
    Assert ($null -eq $r.Error) "one device, no -Serial: no error (got: $($r.Error))"
    Assert ($r.Out -match 'dismissed serial=emulator-5554$') "one device, no -Serial: targets the full serial (got: $($r.Out))"
    Assert ($global:AdbLog -contains '-s emulator-5554 shell input keyevent 4') 'one device: adb -s carries emulator-5554, not a single character'

    $global:DeviceLines = @("List of devices attached", "emulator-5554`tdevice", "R5CW70H129T`tdevice")
    $r = Invoke-Drive 'dismiss-keyboard'
    Assert ($r.Error -match 'Multiple devices') "two devices, no -Serial: still throws 'Multiple devices' (got: $($r.Error))"

    $global:DeviceLines = @("List of devices attached")
    $r = Invoke-Drive 'dismiss-keyboard'
    Assert ($r.Error -match 'No adb devices') "no device: throws 'No adb devices' (got: $($r.Error))"

    $global:DeviceLines = @("List of devices attached", "emulator-5554`tdevice")

    Write-Host '1328: screenshot temp file and secure windows'
    $out = Join-Path $work 'shot.png'
    $r = Invoke-Drive 'screenshot' @{ Out = $out }
    Assert ($null -eq $r.Error) "valid PNG: screenshot succeeds (got: $($r.Error))"
    Assert ($r.Out -match 'pngSize=4x8') "valid PNG: size is reported (got: $($r.Out))"
    Assert ((Test-Path $out)) 'valid PNG: file kept'
    Assert (-not ($global:AdbLog -match '/sdcard/')) 'device temp file is not in /sdcard'
    Assert ($global:AdbLog -match 'screencap -p /data/local/tmp/') 'device temp file is in /data/local/tmp'
    Assert ($global:DeviceFiles.Count -eq 0) 'valid PNG: device temp file removed'

    foreach ($case in @(@{ Name = 'empty file'; Bytes = [byte[]]@() }, @{ Name = 'non-PNG bytes'; Bytes = [byte[]](1..40) })) {
        $out2 = Join-Path $work 'secure.png'
        $global:PullBytes = $case.Bytes
        $r = Invoke-Drive 'screenshot' @{ Out = $out2 }
        Assert ($r.Error -match 'screencap returned no image') "$($case.Name): clear FLAG_SECURE error (got: $($r.Error))"
        Assert ($r.Error -notmatch 'Out of memory') "$($case.Name): not the GDI+ Out of memory message"
        Assert (-not (Test-Path $out2)) "$($case.Name): bad local file deleted"
        Assert ($global:DeviceFiles.Count -eq 0) "$($case.Name): device temp file removed after the failure"
    }
    $global:PullBytes = $goodBytes
} finally {
    Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}

if ($failures.Count -gt 0) {
    Write-Host "`n$($failures.Count) assertion(s) failed"
    exit 1
}
Write-Host "`nall assertions passed"
exit 0
