# Model-file verification for setup.ps1, in its own file so test_setup.ps1 can dot-source it without
# running an install.

# Makes $Target hold the file with this exact length and SHA-256, or throws. A file already there that
# does not match (a half download, or a swapped one of the same size) is removed first so the voice
# can never load it. $Fetch is called with the path to fill; it is written to "$Target.part" and only
# moved into place once it verifies.
function Install-ModelFile {
  param([string]$Target, [long]$Length, [string]$Sha256, [scriptblock]$Fetch)
  if (Test-Path -LiteralPath $Target) {
    if (Test-ModelFile -Path $Target -Length $Length -Sha256 $Sha256) { return }
    Remove-Item -LiteralPath $Target -Force
  }
  $part = "$Target.part"
  if (Test-Path -LiteralPath $part) { Remove-Item -LiteralPath $part -Force }
  & $Fetch $part
  if (-not (Test-ModelFile -Path $part -Length $Length -Sha256 $Sha256)) {
    $got = if (Test-Path -LiteralPath $part) { (Get-FileHash -LiteralPath $part -Algorithm SHA256).Hash.ToLower() } else { 'no file' }
    Remove-Item -LiteralPath $part -Force -ErrorAction SilentlyContinue
    throw "model file $(Split-Path $Target -Leaf) failed verification (expected sha256 $Sha256, got $got)"
  }
  Move-Item -LiteralPath $part -Destination $Target -Force
}

# Length is the cheap pre-check; the hash is what catches a same-size swap.
function Test-ModelFile {
  param([string]$Path, [long]$Length, [string]$Sha256)
  if (-not (Test-Path -LiteralPath $Path)) { return $false }
  if ((Get-Item -LiteralPath $Path).Length -ne $Length) { return $false }
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLower() -eq $Sha256.ToLower()
}
