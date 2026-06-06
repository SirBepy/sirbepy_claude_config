# watch-build.ps1 - companion to the /commit skill's push variants.
# Resolves ALL GitHub Actions runs triggered by a just-pushed commit, blocks until
# every one finishes, and prints a single BUILD_RESULT marker line the agent parses.
# A push can trigger several workflows (test + lint + build as separate workflows);
# watching only the first would miss a failure in any of the others, so we watch and
# aggregate all runs for the sha.
#
# Run in the BACKGROUND. Exit codes: 0 = all succeeded, 1 = >=1 failed, 2 = no run found.

param(
  [Parameter(Mandatory = $true)][string]$Sha,
  [Parameter(Mandatory = $true)][string]$Branch
)

function Get-RunsForSha {
  try {
    $json = gh run list --branch $Branch --limit 30 --json databaseId,headSha,status,workflowName
    if (-not $json) { return @() }
    return @(($json | ConvertFrom-Json) | Where-Object { $_.headSha -eq $Sha })
  } catch { return @() }
}

# Wait for at least one run keyed to this sha to register (CI lags a push by seconds).
# ~3 min ceiling so a repo whose push triggered no CI gives up.
$runs = @()
for ($i = 0; $i -lt 30; $i++) {
  $runs = Get-RunsForSha
  if ($runs.Count -gt 0) { break }
  Start-Sleep -Seconds 6
}

if ($runs.Count -eq 0) {
  Write-Output "BUILD_RESULT=no_run SHA=$Sha"
  exit 2
}

# Sibling workflows may register slightly later than the first. Give them a short
# grace, then take the FULL set of runs for this sha.
Start-Sleep -Seconds 8
$runs = Get-RunsForSha
if ($runs.Count -eq 0) { Write-Output "BUILD_RESULT=no_run SHA=$Sha"; exit 2 }

# Watch every run to completion. They run in parallel on GitHub; watching is sequential
# but a run that already finished returns immediately. --exit-status -> non-zero on failure.
$failed = @()
foreach ($r in $runs) {
  gh run watch $r.databaseId --exit-status | Out-Null
  if ($LASTEXITCODE -ne 0) { $failed += $r }
}

if ($failed.Count -eq 0) {
  $names = ($runs | ForEach-Object { $_.workflowName }) -join ', '
  Write-Output "BUILD_RESULT=success RUNS=$($runs.Count) ($names)"
  exit 0
}

Write-Output "BUILD_RESULT=failure FAILED=$($failed.Count)/$($runs.Count)"
foreach ($r in $failed) {
  Write-Output "----- FAILED: $($r.workflowName) (run $($r.databaseId)) -----"
  gh run view $r.databaseId --log-failed
}
exit 1
