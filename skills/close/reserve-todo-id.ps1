<#
.SYNOPSIS
  Atomically reserve the next free .claude/todos/ backlog id, per ai-todos-format.md's
  "Picking the next id" section.

.DESCRIPTION
  Fixes the max+1 race: two sessions reading the directory at the same moment used to
  compute the same "next" id and both write it. This claims the id itself, using the same
  private-temp-file-then-no-overwrite-rename primitive claim-todo.ps1 already proves works
  for the claims mutex, so a losing caller sees the collision and retries instead of
  silently overwriting another session's file.

  Algorithm per attempt (bounded, default 20):
    1. Prune reservation markers whose mtime is older than 4 hours (mirrors the claims
       staleness rule) so an abandoned reservation cannot inflate ids forever.
    2. Scan .claude/todos/*.md, .claude/todos/done/*.md, and remaining
       .claude/todos/*-.reserved markers for the current max numeric prefix; candidate =
       max + 1. Reserved markers are scanned so two concurrent callers cannot both land on
       max+1 before either has written the real file yet.
    3. Write a private temp file, then Move-Item it onto ".claude/todos/<candidate>-.reserved"
       WITHOUT -Force (fails if the destination exists). Retry once after ~2s on a transient
       Windows filter-driver error before concluding it's a real collision.
    4. Success -> return the candidate id. Collision -> loop (the rescan in step 2 will skip
       past the id that was just taken).

  Reservation lifecycle: the CALLER deletes ".claude/todos/<id>-.reserved" immediately after
  writing the real "<id>-<slug>.md" file. An abandoned reservation (crash between reserve and
  write) self-heals: the next call to this script prunes it once its mtime exceeds 4 hours,
  no separate cleanup skill required.

.PARAMETER RepoRoot
  Project root containing (or to receive) .claude/todos/. Defaults to the current directory.
  Creates .claude/todos/ if missing - this script is meant to run before the first todo in a
  brand new backlog exists.

.PARAMETER MaxAttempts
  Bounded retry count on collision. Default 20.

.OUTPUTS
  Writes the reserved numeric id (and nothing else) to the success stream so a caller can do
  $id = & reserve-todo-id.ps1 -RepoRoot $root. All other messages go via Write-Host.

.EXAMPLE
  $id = & ~/.claude/skills/close/reserve-todo-id.ps1 -RepoRoot C:\Users\joe\Projects\my-app
  # ... write .claude/todos/$id-my-slug.md ...
  Remove-Item (Join-Path $todosDir "$id-.reserved") -Force
#>
param(
    [string]$RepoRoot = (Get-Location).Path,

    [int]$MaxAttempts = 20
)

$ErrorActionPreference = 'Stop'

function Write-Info($msg) { Write-Host $msg }
function Write-Fail($msg) { Write-Error $msg }

$todosDir = Join-Path $RepoRoot '.claude\todos'
$doneDir  = Join-Path $todosDir 'done'

if (-not (Test-Path $todosDir)) {
    New-Item -ItemType Directory -Path $todosDir -Force | Out-Null
}

function Remove-StaleReservations {
    param([string]$TodosDir)
    Get-ChildItem -Path $TodosDir -Filter '*-.reserved' -File -ErrorAction SilentlyContinue |
        ForEach-Object {
            $reservedPid = $null
            $content = Get-Content -Path $_.FullName -Raw -ErrorAction SilentlyContinue
            if ($content -match 'pid:\s*(\d+)') { $reservedPid = [int]$matches[1] }
            $pidAlive = $false
            if ($reservedPid) { $pidAlive = [bool](Get-Process -Id $reservedPid -ErrorAction SilentlyContinue) }
            $ageHours = ((Get-Date) - $_.LastWriteTime).TotalHours
            if ($ageHours -gt 4 -and -not $pidAlive) {
                Remove-Item -Path $_.FullName -Force -ErrorAction SilentlyContinue
            }
        }
}

function Get-MaxId {
    param([string]$TodosDir, [string]$DoneDir)
    $ids = @(0)
    Get-ChildItem -Path $TodosDir -Filter '*.md' -File -ErrorAction SilentlyContinue |
        ForEach-Object { if ($_.Name -match '^0*(\d+)-') { $ids += [int]$matches[1] } }
    if (Test-Path $DoneDir) {
        Get-ChildItem -Path $DoneDir -Filter '*.md' -File -ErrorAction SilentlyContinue |
            ForEach-Object { if ($_.Name -match '^0*(\d+)-') { $ids += [int]$matches[1] } }
    }
    Get-ChildItem -Path $TodosDir -Filter '*-.reserved' -File -ErrorAction SilentlyContinue |
        ForEach-Object { if ($_.Name -match '^0*(\d+)-\.reserved$') { $ids += [int]$matches[1] } }
    return ($ids | Measure-Object -Maximum).Maximum
}

function Try-Rename {
    param([string]$From, [string]$To)
    try {
        Move-Item -Path $From -Destination $To -ErrorAction Stop
        return $true
    }
    catch {
        return $false
    }
}

$sessionId = if ($env:CLAUDE_CODE_SESSION_ID) { $env:CLAUDE_CODE_SESSION_ID } else { "pid-$PID" }
$utf8NoBom = New-Object System.Text.UTF8Encoding $false

$reservedId = $null
$attempt = 0

while ($attempt -lt $MaxAttempts -and -not $reservedId) {
    $attempt++

    Remove-StaleReservations -TodosDir $todosDir
    $candidateId = (Get-MaxId -TodosDir $todosDir -DoneDir $doneDir) + 1

    $markerPath = Join-Path $todosDir "$candidateId-.reserved"
    $tempPath   = Join-Path $todosDir "$candidateId-.reserved.tmp-$PID"

    $content = @(
        "session: $sessionId"
        "pid: $PID"
        "reserved: $((Get-Date).ToUniversalTime().ToString('o'))"
    ) -join "`r`n"
    $content += "`r`n"
    [System.IO.File]::WriteAllText($tempPath, $content, $utf8NoBom)

    $ok = Try-Rename -From $tempPath -To $markerPath
    if (-not $ok) {
        Start-Sleep -Seconds 2
        $ok = Try-Rename -From $tempPath -To $markerPath
    }

    if ($ok) {
        $reservedId = $candidateId
    }
    else {
        Remove-Item -Path $tempPath -Force -ErrorAction SilentlyContinue
        Write-Info "Id $candidateId taken by another caller (attempt $attempt/$MaxAttempts) - retrying."
    }
}

if (-not $reservedId) {
    Write-Fail "Could not reserve a todo id under '$todosDir' after $MaxAttempts attempts."
}

Write-Info "Reserved todo id $reservedId -> .claude\todos\$reservedId-.reserved"
Write-Output $reservedId
