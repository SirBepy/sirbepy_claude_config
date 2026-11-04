# Installs the local narration voice once, outside every repo: Python venv plus Kokoro model files.
# Versions are pinned: they passed the packages safety check on 2026-11-04. Re-run that check before raising one.
# Takes -ModelSource <folder> to copy the model files instead of downloading 350MB.
param([string]$ModelSource = '')
$ErrorActionPreference = 'Stop'

$home_ = Join-Path $env:LOCALAPPDATA 'claude-test-report'
$venv = Join-Path $home_ 'venv'
$models = Join-Path $home_ 'models'
New-Item -ItemType Directory -Force $models | Out-Null

# Kokoro's dependencies had no verified wheels for Python 3.14 when this was written, so it asks for 3.12.
if (-not (Test-Path (Join-Path $venv 'Scripts\python.exe'))) {
  & py -3.12 -m venv $venv
  if ($LASTEXITCODE -ne 0) { throw 'needs Python 3.12: py -3.12 failed' }
}
$python = Join-Path $venv 'Scripts\python.exe'
& $python -m pip install --quiet --upgrade pip
& $python -m pip install --quiet 'kokoro-onnx==0.6.1' 'onnxruntime==1.31.1' 'numpy==2.5.4' 'soundfile==0.14.0' 'phonemizer==3.6.0' 'espeakng-loader==0.2.4'
if ($LASTEXITCODE -ne 0) { throw 'pip install failed' }

$base = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0'
$files = @{ 'kokoro-v1.0.onnx' = 325532387; 'voices-v1.0.bin' = 28214398 }
foreach ($name in $files.Keys) {
  $target = Join-Path $models $name
  if ((Test-Path $target) -and (Get-Item $target).Length -eq $files[$name]) { continue }
  if ($ModelSource) { Copy-Item (Join-Path $ModelSource $name) $target -Force }
  else { Invoke-WebRequest "$base/$name" -OutFile $target }
  if ((Get-Item $target).Length -ne $files[$name]) { throw "wrong size for $name" }
}
Write-Output "voice ready in $home_"
