# watch-build.ps1 - companion to the /commit skill's push variants.
# Resolves ALL GitHub Actions runs triggered by a just-pushed commit, blocks until
# every one finishes, and prints a single BUILD_RESULT marker line the agent parses.
# A push can trigger several workflows (test + lint + build as separate workflows);
# watching only the first would miss a failure in any of the others, so we watch and
# aggregate all runs for the sha.
#
# Run in the BACKGROUND. Exit codes: 0 = all succeeded, 1 = >=1 failed, 2 = no run found,
# 3 = watch_error, 4 = timeout.

param(
  [string]$Sha,
  [Parameter(Mandatory = $true)][string]$Branch, # kept for the caller's convention; no longer used to filter runs, see Get-RunsForSha
  [string]$RepoPath = (Get-Location).Path,
  [int]$TimeoutMinutes = 30
)

# PID file next to this script so a session can kill a stuck watcher:
# Stop-Process -Id (Get-Content <this file>) -Force. Cleaned up in the
# top-level `finally` below regardless of which exit path is taken.
$PidFile = Join-Path $PSScriptRoot "watch-build.pid"
Set-Content -Path $PidFile -Value $PID

# Wall-clock ceiling for the whole watch: bounds `gh run watch`, which
# otherwise blocks until the run completes and would leave this background
# process running indefinitely against a genuinely hung CI job.
$ScriptStart = Get-Date
$TimeoutDeadline = $ScriptStart.AddMinutes($TimeoutMinutes)

try {

# -Sha is optional and self-healing: if omitted, or if it doesn't look like a full
# 40-char hex sha (e.g. a hand-typed/truncated sha), resolve the real HEAD sha from
# -RepoPath instead of trusting the caller's value. This closes the enforcement gap
# where a fabricated sha silently watched nothing.
if ([string]::IsNullOrWhiteSpace($Sha) -or ($Sha -notmatch '^[0-9a-fA-F]{40}$')) {
  $badSha = $Sha
  try {
    $Sha = (git -C $RepoPath rev-parse HEAD).Trim()
  } catch {
    Write-Output "BUILD_RESULT=no_run SHA=$badSha ERROR=could_not_resolve_head"
    exit 2
  }
  if ($Sha -notmatch '^[0-9a-fA-F]{40}$') {
    Write-Output "BUILD_RESULT=no_run SHA=$badSha ERROR=could_not_resolve_head"
    exit 2
  }
  if ($badSha) {
    Write-Output "NOTE: malformed -Sha '$badSha' rejected; resolved HEAD instead -> $Sha"
  }
}

# gh has no cwd of its own here - it infers the repo from the CALLING shell's
# cwd, not from -RepoPath. If the watcher is launched while that shell sits in
# a different repo (common across a multi-repo session), every gh call below
# silently targets the wrong repo (or none) and looks like "no run exists".
# Resolve the slug from -RepoPath once and pin it explicitly on every call.
Push-Location $RepoPath
try {
  $RepoSlug = (gh repo view --json nameWithOwner -q .nameWithOwner).Trim()
} catch {
  $RepoSlug = $null
} finally {
  Pop-Location
}
if ([string]::IsNullOrWhiteSpace($RepoSlug)) {
  Write-Output "BUILD_RESULT=no_run SHA=$Sha ERROR=could_not_resolve_repo"
  exit 2
}

function Get-RunsForSha {
  # No --branch filter: headBranch mismatches $Branch for tag-triggered runs (todo 371).
  try {
    $json = gh run list -R $RepoSlug --limit 50 --json databaseId,headSha,status,workflowName
    if (-not $json) { return @() }
    return @(($json | ConvertFrom-Json) | Where-Object { $_.headSha -eq $Sha })
  } catch {
    $script:LastGhError = $_.Exception.Message -replace '[\r\n]+', ' '
    $script:GhErrorCount++
    return @()
  }
}

# Wait for at least one run keyed to this sha to register (CI lags a push by seconds).
# ~3 min ceiling so a repo whose push triggered no CI gives up.
$runs = @()
$GhErrorCount = 0
$LastGhError = $null
$pollCount = 0
for ($i = 0; $i -lt 30; $i++) {
  $pollCount++
  $runs = Get-RunsForSha
  if ($runs.Count -gt 0) { break }
  Start-Sleep -Seconds 6
}

if ($runs.Count -eq 0) {
  # Every poll erroring (vs. genuinely returning an empty list) means the API
  # was unreachable, not that no run exists - don't conflate the two.
  if ($GhErrorCount -ge $pollCount) {
    Write-Output "BUILD_RESULT=api_error LAST_ERROR=$LastGhError"
    exit 2
  }
  Write-Output "BUILD_RESULT=no_run SHA=$Sha"
  exit 2
}

# Sibling workflows may register slightly later than the first. Give them a short
# grace, then take the FULL set of runs for this sha.
Start-Sleep -Seconds 8
$runs = Get-RunsForSha
if ($runs.Count -eq 0) { Write-Output "BUILD_RESULT=no_run SHA=$Sha"; exit 2 }

# `gh run watch --exit-status` exits non-zero both when the run genuinely
# finished with a failing conclusion AND when gh itself hit a transient API
# error (e.g. a concurrent session's account-switch hook flipping gh's active
# account mid-poll, a dropped connection, a rate limit). Those two cases are
# NOT the same thing - only the first is a real build result. So after watch
# returns, positively confirm the run's actual status via `gh run view` before
# deciding anything; if the run isn't actually reported completed, that was a
# transient watch error, not a failure - retry with backoff instead of
# concluding failure on a run that's still in progress.
function Get-RunConclusion {
  param([Parameter(Mandatory = $true)]$RunId)
  try {
    $json = gh run view $RunId -R $RepoSlug --json status,conclusion
    if (-not $json) { return $null }
    return ($json | ConvertFrom-Json)
  } catch {
    return $null
  }
}

function Wait-ForRunCompletion {
  param([Parameter(Mandatory = $true)]$Run)
  $maxAttempts = 3
  $backoffSeconds = @(20, 40, 60) # ~2 min total across retries, per todo 198's spec
  for ($attempt = 1; $attempt -le $maxAttempts; $attempt++) {
    $remainingSeconds = ($TimeoutDeadline - (Get-Date)).TotalSeconds
    if ($remainingSeconds -le 0) { return @{ Outcome = 'timeout' } }
    $remaining = [int][Math]::Ceiling($remainingSeconds)

    # Run `gh run watch` as a job so it can be force-stopped at the deadline -
    # a bare synchronous call has no timeout of its own and would otherwise
    # block this whole process against a genuinely hung CI run.
    $job = Start-Job -ScriptBlock {
      param($RunId, $Slug)
      gh run watch $RunId -R $Slug --exit-status | Out-Null
      $LASTEXITCODE
    } -ArgumentList $Run.databaseId, $RepoSlug

    $finished = Wait-Job -Job $job -Timeout $remaining
    if (-not $finished) {
      Stop-Job -Job $job -ErrorAction SilentlyContinue
      Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
      return @{ Outcome = 'timeout' }
    }
    $watchExit = Receive-Job -Job $job
    Remove-Job -Job $job -Force -ErrorAction SilentlyContinue

    $info = Get-RunConclusion -RunId $Run.databaseId
    if ($info -and $info.status -eq 'completed') {
      # Only failure/timed_out are red; skipped/cancelled/neutral are not (todo 371).
      if ($info.conclusion -in @('failure', 'timed_out')) {
        return @{ Outcome = 'failure'; Conclusion = $info.conclusion }
      }
      return @{ Outcome = 'success'; Conclusion = $info.conclusion }
    }

    # watch exited but gh does not positively confirm completion -> transient
    # API hiccup, not a build result. Retry unless attempts are exhausted.
    if ($attempt -lt $maxAttempts) {
      $remaining = ($TimeoutDeadline - (Get-Date)).TotalSeconds
      if ($remaining -le 0) { return @{ Outcome = 'timeout' } }
      $statusText = if ($info) { $info.status } else { 'unknown' }
      $sleepFor = [Math]::Min($backoffSeconds[$attempt - 1], $remaining)
      Write-Output "NOTE: transient watch error on run $($Run.databaseId) (attempt $attempt/$maxAttempts, watch exit=$watchExit, status=$statusText); retrying in ${sleepFor}s"
      Start-Sleep -Seconds $sleepFor
    }
  }
  return @{ Outcome = 'watch_error' }
}

# Watch every run to completion. They run in parallel on GitHub; watching is sequential
# but a run that already finished returns immediately. Stops early on a timeout so
# remaining unwatched runs don't extend the wall-clock ceiling further.
$failed = @()
$watchErrors = @()
$nonSuccess = @()
$timedOut = $false
foreach ($r in $runs) {
  $result = Wait-ForRunCompletion -Run $r
  if ($result.Outcome -eq 'failure') { $failed += $r }
  elseif ($result.Outcome -eq 'watch_error') { $watchErrors += $r }
  elseif ($result.Outcome -eq 'timeout') { $timedOut = $true; break }
  elseif ($result.Outcome -eq 'success' -and $result.Conclusion -and $result.Conclusion -ne 'success') {
    $nonSuccess += "$($r.workflowName)=$($result.Conclusion)"
  }
}

if ($timedOut) {
  Write-Output "BUILD_RESULT=timeout TIMEOUT_MINUTES=$TimeoutMinutes RUNS=$($runs.Count)"
  exit 4
}

if ($failed.Count -eq 0 -and $watchErrors.Count -eq 0) {
  $names = ($runs | ForEach-Object { $_.workflowName }) -join ', '
  Write-Output "BUILD_RESULT=success RUNS=$($runs.Count) ($names)"
  # skipped/cancelled conclusions still deserve a callout (build-watch.md reporting discipline).
  if ($nonSuccess.Count -gt 0) {
    Write-Output "NOTE: non-success conclusions (not failures): $($nonSuccess -join ', ')"
  }
  exit 0
}

if ($failed.Count -gt 0) {
  Write-Output "BUILD_RESULT=failure FAILED=$($failed.Count)/$($runs.Count)"
  foreach ($r in $failed) {
    Write-Output "----- FAILED: $($r.workflowName) (run $($r.databaseId)) -----"
    gh run view $r.databaseId -R $RepoSlug --log-failed
  }
  exit 1
}

# No confirmed failures, but one or more runs never resolved to a completed
# status after retries - a persistent gh/API problem, not a build verdict.
# Distinct marker so the agent knows to relaunch the watcher rather than
# diagnose a build that may not have actually failed.
$names = ($watchErrors | ForEach-Object { $_.workflowName }) -join ', '
Write-Output "BUILD_RESULT=watch_error RUNS_UNRESOLVED=$($watchErrors.Count)/$($runs.Count) ($names)"
exit 3

} finally {
  Remove-Item -Path $PidFile -Force -ErrorAction SilentlyContinue
}
