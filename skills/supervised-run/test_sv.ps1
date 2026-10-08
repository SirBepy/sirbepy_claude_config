<#
.SYNOPSIS
  Self-test for sv.ps1's pure helpers (todo 1132), run via ci/run_all.py's
  skill-script discovery.

.DESCRIPTION
  Dot-sources sv-lib.ps1 directly - never sv.ps1 itself, never a running
  server_supervisor - so these assertions exercise Get-ParamsHash,
  Format-StartedAt and Get-ApiErrorBody in isolation. Exits 0 on pass, 1 on
  any failed assertion, same contract as test-archive-batch.ps1.
#>
$ErrorActionPreference = 'Stop'

$failures = New-Object System.Collections.Generic.List[string]
function Assert($Condition, $Message) {
    if ($Condition) { Write-Host "  PASS: $Message" }
    else { $failures.Add($Message); Write-Host "  FAIL: $Message" }
}

. (Join-Path $PSScriptRoot 'sv-lib.ps1')

# --- Get-ParamsHash ---

Write-Host "=== Get-ParamsHash ==="

$noArgs = Get-ParamsHash $null
Assert ($null -eq $noArgs) "no -Param args -> `$null"

$one = Get-ParamsHash @('device=chrome')
Assert ($one.Count -eq 1) "single -Param: hash has 1 entry (got $($one.Count))"
Assert ($one['device'] -eq 'chrome') "single -Param: device=chrome round-trips"

# The acceptance criterion this guards: a mutated Get-ParamsHash that only
# keeps the LAST -Param (e.g. assigning into a fresh hash per iteration
# instead of accumulating) would still pass a one-entry check above but
# fail here on the second key.
$several = Get-ParamsHash @('device=chrome', 'flavor=dev')
Assert ($several.Count -eq 2) "several -Param: hash has 2 entries (got $($several.Count))"
Assert ($several['device'] -eq 'chrome') "several -Param: FIRST key 'device' is present"
Assert ($several['flavor'] -eq 'dev') "several -Param: SECOND key 'flavor' is present"

$withEquals = Get-ParamsHash @('url=http://x?a=b')
Assert ($withEquals['url'] -eq 'http://x?a=b') "value containing '=' keeps everything after the FIRST '=' (got '$($withEquals['url'])')"

# Malformed entry (no '='): current code calls Write-Fail -> Write-Error, which
# is a terminating error under `$ErrorActionPreference = 'Stop'` (set above,
# matching sv.ps1's own top-of-script setting) - so Get-ParamsHash throws
# rather than skipping the bad entry.
$malformedThrew = $false
$malformedMessage = $null
try {
    Get-ParamsHash @('noequalsign') | Out-Null
}
catch {
    $malformedThrew = $true
    $malformedMessage = $_.Exception.Message
}
Assert $malformedThrew "malformed '-Param' (no '=') throws a terminating error"
Assert ($malformedMessage -like '*-Param must be name=value*noequalsign*') "malformed '-Param' error names the offending value (got: '$malformedMessage')"

# --- Format-StartedAt ---

Write-Host "=== Format-StartedAt ==="

Assert ((Format-StartedAt $null) -eq '') "no started_at -> empty string"
Assert ((Format-StartedAt '') -eq '') "empty-string started_at -> empty string"

# 1700000000000 ms = 2023-11-14T22:13:20Z (verified via
# [DateTimeOffset]::FromUnixTimeMilliseconds(1700000000000).UtcDateTime).
$since = Format-StartedAt 1700000000000
Assert ($since -eq ' since=2023-11-14T22:13:20Z') "known epoch-millis formats to the expected UTC string (got '$since')"

# --- Get-ApiErrorBody ---

Write-Host "=== Get-ApiErrorBody ==="

# No HTTP response on the exception (e.g. a connection-level failure) ->
# falls back to the plain exception message, with no network I/O involved.
$fakeErr = [PSCustomObject]@{
    Exception = [PSCustomObject]@{ Response = $null; Message = 'connection refused' }
}
Assert ((Get-ApiErrorBody $fakeErr) -eq 'connection refused') "no Response on the exception -> falls back to Exception.Message"

if ($failures.Count -gt 0) {
    Write-Host ""
    Write-Host "FAIL: $($failures.Count) assertion(s) failed:"
    $failures | ForEach-Object { Write-Host "  - $_" }
    exit 1
}
Write-Host ""
Write-Host "OK: all assertions passed"
exit 0
