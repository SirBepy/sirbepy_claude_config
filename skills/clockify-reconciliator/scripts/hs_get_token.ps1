# Exchanges HUBSTAFF_REFRESH_TOKEN for an access_token, per hubstaff.md Step 11.
# Prints ONLY the access_token to stdout. Never echoes the refresh token.
#
# Caches the access token outside the repo (CachePath) so a run that needs the token more than
# once (hubstaff.md step 11 pre/post re-fetch, step 12) does not rotate the refresh token on every
# call - a second exchange within one run risks the HubStaff rate limit (todo 997, 2026-09-23
# incident). The cache lives under %LOCALAPPDATA%, never inside this repo, and is never printed.
param(
    [string]$EnvPath = "$HOME/.claude/.env",
    [string]$CachePath = "$env:LOCALAPPDATA\claude-clockify\hubstaff-access-token.json"
)

$ErrorActionPreference = 'Stop'

function Get-CachedAccessToken {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $null }
    try {
        $cached = Get-Content -Path $Path -Raw | ConvertFrom-Json
        $expiresAt = [datetime]::Parse($cached.expires_at, [System.Globalization.CultureInfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::RoundtripKind)
    } catch {
        # Malformed cache (bad JSON, missing/unparseable fields) degrades to a real exchange
        # rather than crashing - the cache is a speed-up, never a hard dependency.
        return $null
    }
    if (-not $cached.access_token) { return $null }
    # 60s safety margin so a token already in flight doesn't expire mid-call.
    if ((Get-Date).ToUniversalTime().AddSeconds(60) -lt $expiresAt) { return $cached.access_token }
    return $null
}

function Save-AccessToken {
    param([string]$Path, [string]$AccessToken, [datetime]$ExpiresAt)
    $cacheDir = Split-Path -Path $Path -Parent
    if ($cacheDir -and -not (Test-Path $cacheDir)) { New-Item -ItemType Directory -Path $cacheDir -Force | Out-Null }
    $cacheObj = @{ access_token = $AccessToken; expires_at = $ExpiresAt.ToString('o') }
    [System.IO.File]::WriteAllText($Path, ($cacheObj | ConvertTo-Json))
    # Best-effort: this file holds a live bearer token, restrict it to the current user.
    try { icacls $Path /inheritance:r /grant:r "$($env:USERNAME):(R,W)" | Out-Null } catch {}
}

$cachedToken = Get-CachedAccessToken -Path $CachePath
if ($cachedToken) {
    Write-Output $cachedToken
    return
}

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

# HubStaff names its own lifetime in expires_in (seconds); fall back to the 24h window this
# cache was designed against (todo 997) if the field is ever absent from the response.
$expiresInSec = if ($response.expires_in) { [int]$response.expires_in } else { 24 * 3600 }
Save-AccessToken -Path $CachePath -AccessToken $response.access_token -ExpiresAt ((Get-Date).ToUniversalTime().AddSeconds($expiresInSec))

Write-Output $response.access_token
