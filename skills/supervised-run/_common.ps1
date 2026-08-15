<#
.SYNOPSIS
  Shared server_supervisor connection helpers for sv.ps1 and restart-and-wait.ps1.

.DESCRIPTION
  Dot-source this from a script's own directory (`. (Join-Path $PSScriptRoot '_common.ps1')`)
  so token/port resolution lives in one place. Has no param() block itself - it only
  defines $dataDir and the two functions below.
#>

$dataDir = Join-Path $env:APPDATA 'com.sirbepy.server-supervisor\supervisor'

# Returns $null (not a throw) when the supervisor isn't running - callers treat
# that as "go to Fallback", never as a script error.
function Get-SupervisorConfig {
    $tokenPath = Join-Path $dataDir 'api_token.txt'
    $portPath = Join-Path $dataDir 'api_port.txt'
    if (-not (Test-Path $tokenPath) -or -not (Test-Path $portPath)) { return $null }
    $token = (Get-Content -Path $tokenPath -Raw).Trim()
    $port = (Get-Content -Path $portPath -Raw).Trim()
    if (-not $token -or -not $port) { return $null }
    return [pscustomobject]@{ Token = $token; Port = $port; BaseUrl = "http://127.0.0.1:$port" }
}

# Token only ever goes into this header, never into Write-Host/Write-Info output.
function Invoke-Api($cfg, $Method, $Path, $Body) {
    $headers = @{ Authorization = "Bearer $($cfg.Token)" }
    $uri = "$($cfg.BaseUrl)$Path"
    if ($Body) {
        Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -Body ($Body | ConvertTo-Json -Depth 5) -ContentType 'application/json'
    }
    else {
        Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers
    }
}
