# Installs the local narration voice once, outside every repo: Python venv plus Kokoro model files.
# The packages are the hashed closure in requirements-voice.txt (the 16 wheels that passed the packages
# safety check on 2026-11-04, transitive ones included) and the two model files are checked by SHA-256, so
# a re-run on any machine gets exactly what was audited. Re-run that check before raising a version, then
# regenerate the requirements file; never edit a hash by hand.
# The model hashes are those of the files installed on 2026-11-04; the upstream release publishes sizes
# only, so they are pinned to that copy rather than to an upstream digest.
# Takes -ModelSource <folder> to copy the model files instead of downloading 350MB.
# Takes -ModelsOnly to fetch and verify the model files and skip the venv.
# TEST_REPORT_HOME moves the install folder, the same variable tts-client.cjs reads.
param([string]$ModelSource = '', [switch]$ModelsOnly)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'setup-lib.ps1')

$home_ = if ($env:TEST_REPORT_HOME) { $env:TEST_REPORT_HOME } else { Join-Path $env:LOCALAPPDATA 'claude-test-report' }
$venv = Join-Path $home_ 'venv'
$models = Join-Path $home_ 'models'
New-Item -ItemType Directory -Force $models | Out-Null

if (-not $ModelsOnly) {
  # Kokoro's dependencies had no verified wheels for Python 3.14 when this was written, so it asks for 3.12.
  if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
    & py -3.12 -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw 'needs Python 3.12: py -3.12 failed' }
  }
  $python = Join-Path $venv 'Scripts\python.exe'
  & $python -m pip install --quiet --upgrade pip
  # --require-hashes refuses any package or file the requirements file does not list with a hash.
  & $python -m pip install --quiet --require-hashes --only-binary=:all: -r (Join-Path $PSScriptRoot 'requirements-voice.txt')
  if ($LASTEXITCODE -ne 0) { throw 'pip install failed' }
}

$base = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0'
$files = [ordered]@{
  'kokoro-v1.0.onnx' = @{ Length = 325532387; Sha256 = '7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5' }
  'voices-v1.0.bin'  = @{ Length = 28214398;  Sha256 = 'bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d' }
}
foreach ($name in $files.Keys) {
  $target = Join-Path $models $name
  $fetch = if ($ModelSource) { { param($dest) Copy-Item (Join-Path $ModelSource $name) $dest -Force }.GetNewClosure() }
           else { { param($dest) Invoke-WebRequest "$base/$name" -OutFile $dest }.GetNewClosure() }
  Install-ModelFile -Target $target -Length $files[$name].Length -Sha256 $files[$name].Sha256 -Fetch $fetch
}
Write-Output "voice ready in $home_"
