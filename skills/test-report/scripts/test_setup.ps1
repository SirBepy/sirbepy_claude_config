<#
.SYNOPSIS
  Self-test for setup.ps1's model verification and the hashed requirements file. Installs nothing.

.DESCRIPTION
  Dot-sources setup-lib.ps1 against tiny fake files, runs setup.ps1 -ModelsOnly against a temp
  TEST_REPORT_HOME with a tampered model source (it must fail), and lints requirements-voice.txt.
  With -WithRealModels it also copies the installed Kokoro model files into the temp home and
  expects setup.ps1 -ModelsOnly to accept them (copies 350MB).

.PARAMETER WithRealModels
  Also prove the pinned model hashes against the files installed under %LOCALAPPDATA%.
#>
param([switch]$WithRealModels)
$ErrorActionPreference = 'Stop'

$failures = New-Object System.Collections.Generic.List[string]
function Assert($Condition, $Message) {
  if ($Condition) { Write-Host "  PASS: $Message" }
  else { $failures.Add($Message); Write-Host "  FAIL: $Message" }
}

# Runs setup.ps1 in a child pwsh and returns its merged output. Windows PowerShell 5.1 wraps each
# native stderr line in an ErrorRecord that $ErrorActionPreference='Stop' turns into a terminating
# NativeCommandError, and the failure paths under test write to stderr on purpose. 'Continue' keeps
# the expected stderr as plain output; $LASTEXITCODE still carries the child's real exit code.
function Invoke-Setup([string[]]$SetupArgs) {
  $saved = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try { & pwsh -NoProfile -File (Join-Path $PSScriptRoot 'setup.ps1') @SetupArgs 2>&1 | Out-String }
  finally { $ErrorActionPreference = $saved }
}

. (Join-Path $PSScriptRoot 'setup-lib.ps1')

$work = Join-Path ([System.IO.Path]::GetTempPath()) ('test-report-setup-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $work -Force
try {
  Write-Host 'Install-ModelFile with fake files'
  $good = [System.Text.Encoding]::ASCII.GetBytes('good model bytes')
  $evil = [System.Text.Encoding]::ASCII.GetBytes('evil model bytes')   # same length as $good
  $sha = (Get-FileHash -InputStream ([System.IO.MemoryStream]::new($good)) -Algorithm SHA256).Hash.ToLower()
  $fetchGood = { param($dest) [System.IO.File]::WriteAllBytes($dest, $good) }
  $fetchEvil = { param($dest) [System.IO.File]::WriteAllBytes($dest, $evil) }

  $t = Join-Path $work 'a.bin'
  Install-ModelFile -Target $t -Length $good.Length -Sha256 $sha -Fetch $fetchGood
  Assert ([System.IO.File]::ReadAllBytes($t).Length -eq $good.Length) 'a verified fetch lands at the target'
  Assert (-not (Test-Path "$t.part")) 'no .part file is left after success'

  $calls = 0
  Install-ModelFile -Target $t -Length $good.Length -Sha256 $sha -Fetch { param($dest) $script:calls++ }
  Assert ($calls -eq 0) 'a valid file already in place is not fetched again'

  $t2 = Join-Path $work 'b.bin'
  $threw = $false
  try { Install-ModelFile -Target $t2 -Length $good.Length -Sha256 $sha -Fetch $fetchEvil } catch { $threw = $true; $msg = $_.Exception.Message }
  Assert $threw 'a same-size tampered download is refused'
  Assert ($msg -match 'failed verification') "the error names the verification failure (got: $msg)"
  Assert (-not (Test-Path $t2)) 'the tampered download is never moved into place'
  Assert (-not (Test-Path "$t2.part")) 'the tampered .part file is deleted'

  $t3 = Join-Path $work 'c.bin'
  [System.IO.File]::WriteAllBytes($t3, $evil)
  Install-ModelFile -Target $t3 -Length $good.Length -Sha256 $sha -Fetch $fetchGood
  Assert ([System.IO.File]::ReadAllBytes($t3)[0] -eq $good[0]) 'a same-size tampered file already in place is replaced by a verified one'

  $t4 = Join-Path $work 'd.bin'
  [System.IO.File]::WriteAllBytes($t4, $evil)
  $threw = $false
  try { Install-ModelFile -Target $t4 -Length $good.Length -Sha256 $sha -Fetch $fetchEvil } catch { $threw = $true }
  Assert ($threw -and -not (Test-Path $t4)) 'a tampered file in place plus a tampered download leaves nothing usable'

  Write-Host 'setup.ps1 -ModelsOnly against a tampered model source'
  $home1 = Join-Path $work 'home1'
  $src = Join-Path $work 'src'
  $null = New-Item -ItemType Directory -Path $src -Force
  [System.IO.File]::WriteAllBytes((Join-Path $src 'kokoro-v1.0.onnx'), $evil)
  [System.IO.File]::WriteAllBytes((Join-Path $src 'voices-v1.0.bin'), $evil)
  $env:TEST_REPORT_HOME = $home1
  $out = Invoke-Setup '-ModelsOnly', '-ModelSource', $src
  Assert ($LASTEXITCODE -ne 0) 'setup.ps1 exits non-zero on a tampered model'
  Assert ($out -match 'failed verification') 'setup.ps1 reports the verification failure'
  Assert (-not (Test-Path (Join-Path $home1 'models\kokoro-v1.0.onnx'))) 'no model file is installed from a tampered source'
  Assert (-not (Test-Path (Join-Path $home1 'venv'))) '-ModelsOnly creates no venv'

  if ($WithRealModels) {
    Write-Host 'setup.ps1 -ModelsOnly with the real installed models'
    $realModels = Join-Path $env:LOCALAPPDATA 'claude-test-report\models'
    $env:TEST_REPORT_HOME = Join-Path $work 'home2'
    $out = Invoke-Setup '-ModelsOnly', '-ModelSource', $realModels
    Assert ($LASTEXITCODE -eq 0) "setup.ps1 accepts the real model files (output: $out)"
    Assert (Test-Path (Join-Path $env:TEST_REPORT_HOME 'models\kokoro-v1.0.onnx')) 'the verified model is installed'
  }

  Write-Host 'requirements-voice.txt'
  $req = [System.IO.File]::ReadAllText((Join-Path $PSScriptRoot 'requirements-voice.txt')) -replace "`r", ''
  # Join "\"-continued lines into one entry per package.
  $entries = ($req -replace "\\\n\s*", ' ').Split("`n") | Where-Object { $_.Trim() -and -not $_.TrimStart().StartsWith('#') }
  Assert ($entries.Count -ge 6) "lists the closure, not just the six top-level packages ($($entries.Count) entries)"
  foreach ($e in $entries) {
    $name = ($e -split '\s')[0]
    Assert ($name -match '^[A-Za-z0-9._-]+==\S+$') "$name is pinned with =="
    Assert ($e -match '--hash=sha256:[0-9a-f]{64}') "$name carries at least one sha256 hash"
  }
  foreach ($top in 'kokoro-onnx', 'onnxruntime', 'numpy', 'soundfile', 'phonemizer', 'espeakng-loader') {
    Assert (($entries | Where-Object { $_ -match "^$([regex]::Escape($top))==" }).Count -eq 1) "$top is listed once"
  }
} finally {
  Remove-Item Env:\TEST_REPORT_HOME -ErrorAction SilentlyContinue
  Remove-Item -LiteralPath $work -Recurse -Force -ErrorAction SilentlyContinue
}

if ($failures.Count -gt 0) {
  Write-Host "`n$($failures.Count) assertion(s) failed"
  exit 1
}
Write-Host "`nall assertions passed"
exit 0
