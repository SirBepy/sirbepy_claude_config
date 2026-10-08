<#
.SYNOPSIS
  sv.ps1's pure helpers, split out so a test can call them directly (todo 1132).

.DESCRIPTION
  Dot-source this from a script's own directory, same convention as _common.ps1
  (`. (Join-Path $PSScriptRoot 'sv-lib.ps1')`). Nothing here touches the network
  or the filesystem outside what the caller passes in - that is what makes
  test_sv.ps1 able to call them without running the CLI or contacting
  server_supervisor.
#>

function Write-Info($msg) { Write-Host $msg }
function Write-Fail($msg) { Write-Error $msg }

# started_at is Unix epoch millis (ProcInfo.started_at); "" when the API omitted it
# (stopped entry, or an older server_supervisor build without the field) so callers
# never print a bogus "since=" on every ensure.
function Format-StartedAt($epochMs) {
    if (-not $epochMs) { return '' }
    $dt = [DateTimeOffset]::FromUnixTimeMilliseconds([int64]$epochMs).UtcDateTime
    return " since=$($dt.ToString('yyyy-MM-ddTHH:mm:ssZ'))"
}

# "-Param device=chrome" (repeatable) -> @{ device = 'chrome' }. Split on the FIRST
# '=' only, so a value containing '=' (unlikely but not impossible for a free-text
# axis) still round-trips.
function Get-ParamsHash($paramArgs) {
    if (-not $paramArgs) { return $null }
    $hash = @{}
    foreach ($p in $paramArgs) {
        $idx = $p.IndexOf('=')
        if ($idx -lt 1) { Write-Fail "-Param must be name=value, got: $p" }
        $hash[$p.Substring(0, $idx)] = $p.Substring($idx + 1)
    }
    return $hash
}

# Invoke-RestMethod's own exception text drops the response body, so a 400's actual
# "unknown param/value, valid ones are: ..." message (server_supervisor
# supervisor/crud/params.rs validate_selection) never reaches the caller without this.
function Get-ApiErrorBody($err) {
    $resp = $err.Exception.Response
    if (-not $resp) { return $err.Exception.Message }
    try {
        $stream = $resp.GetResponseStream()
        $reader = New-Object System.IO.StreamReader($stream)
        $text = $reader.ReadToEnd()
        if ($text) { return $text }
    }
    catch { }
    return $err.Exception.Message
}
