# Exchanges HUBSTAFF_REFRESH_TOKEN for an access_token, per hubstaff.md Step 11.
# Prints ONLY the access_token to stdout. Never echoes the refresh token.
param(
    [string]$EnvPath = "$HOME/.claude/.env"
)

$ErrorActionPreference = 'Stop'

if (-not (Test-Path $EnvPath)) {
    Write-Error "env file not found: $EnvPath"
    exit 1
}

$lines = Get-Content -Path $EnvPath
$tokenLine = $lines | Where-Object { $_ -match '^HUBSTAFF_REFRESH_TOKEN=' }
if (-not $tokenLine) {
    Write-Error "HUBSTAFF_REFRESH_TOKEN not set in $EnvPath"
    exit 1
}
$refreshToken = $tokenLine.Substring('HUBSTAFF_REFRESH_TOKEN='.Length)

# account.hubstaff.com sits behind Cloudflare; default library agents get 403 error 1010.
$headers = @{ 'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36' }
$body = "grant_type=refresh_token&refresh_token=$refreshToken"
$response = Invoke-RestMethod -Uri 'https://account.hubstaff.com/access_tokens' -Method Post -Headers $headers -Body $body -ContentType 'application/x-www-form-urlencoded'

# Rotates on every exchange; the old value is worthless the instant this call succeeds.
$backupPath = "$EnvPath.bak"
Copy-Item -Path $EnvPath -Destination $backupPath -Force

$newLines = $lines | ForEach-Object {
    if ($_ -match '^HUBSTAFF_REFRESH_TOKEN=') { "HUBSTAFF_REFRESH_TOKEN=$($response.refresh_token)" } else { $_ }
}
[System.IO.File]::WriteAllLines($EnvPath, $newLines)

Write-Output $response.access_token
