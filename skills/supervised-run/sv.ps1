<#
.SYNOPSIS
  Talk to server_supervisor without re-deriving the token/port/procs dance every run.

.DESCRIPTION
  Wraps the API documented in SKILL.md: reads api_token.txt/api_port.txt, health-checks,
  and exposes verb subcommands so /supervised-run calls `sv.ps1 ensure ...` once instead
  of restating the reuse/start/restart decision tree in prose each time.

  `ensure` disambiguates reuse by absolute ROOT (from projects.json), not just project
  name - a git worktree of the same project has its own root and must never reuse
  another worktree's process (todo 20; incident 2026-07-15, frontend-3 served stale UI).

.PARAMETER Command
  ls | ensure | logs | stop | restart | rm

.PARAMETER Project
  (ensure) Project folder name, e.g. "frontend" - matches /procs' "project" field.

.PARAMETER Cmd
  (ensure) The exact command string to run/match, {PORT}-templated if dynamic.

.PARAMETER Root
  (ensure) Absolute project root. Defaults to the current directory.

.PARAMETER Kind
  (ensure) "generic" or "flutter" for a first-time /run. Defaults to "generic".

.PARAMETER NoDynamicPort
  (ensure) Skip {PORT} templating on a first-time /run; accept the tool's own port.

.PARAMETER Restart
  (ensure) Force a running match to pick up code changes: /reload for flutter, /restart
  otherwise. Without this switch, a running match is left alone.

.PARAMETER Id
  (logs|stop|restart|rm) Proc id, form "<project>:<name>".

.EXAMPLE
  sv.ps1 ls
  sv.ps1 ensure -Project frontend -Cmd "npm run dev -- --port {PORT}"
  sv.ps1 ensure -Project frontend -Cmd "npm run dev -- --port {PORT}" -Restart
  sv.ps1 logs -Id frontend:dev
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateSet('ls', 'ensure', 'logs', 'stop', 'restart', 'rm')]
    [string]$Command,

    [string]$Project,
    [string]$Cmd,
    [string]$Root = (Get-Location).Path,
    [string]$Kind = 'generic',
    [switch]$NoDynamicPort,
    [switch]$Restart,
    [string]$Id
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_common.ps1')

function Write-Info($msg) { Write-Host $msg }
function Write-Fail($msg) { Write-Error $msg }

function Test-SupervisorHealth($cfg) {
    try {
        $r = Invoke-WebRequest -Uri "$($cfg.BaseUrl)/health" -UseBasicParsing -TimeoutSec 5
        return $r.StatusCode -eq 200
    }
    catch {
        return $false
    }
}

function Require-Supervisor {
    $cfg = Get-SupervisorConfig
    if (-not $cfg -or -not (Test-SupervisorHealth $cfg)) {
        Write-Fail "supervisor not reachable - fall back to a plain shell run."
    }
    return $cfg
}

function Get-ProjectsRegistry {
    $path = Join-Path $dataDir 'projects.json'
    if (-not (Test-Path $path)) { return @() }
    return Get-Content -Path $path -Raw | ConvertFrom-Json
}

function Normalize-RootPath($p) {
    if (-not $p) { return $p }
    return ($p -replace '\\', '/').TrimEnd('/').ToLowerInvariant()
}

switch ($Command) {
    'ls' {
        $cfg = Get-SupervisorConfig
        if (-not $cfg -or -not (Test-SupervisorHealth $cfg)) {
            Write-Info "supervisor not reachable."
            exit 2
        }
        $procs = Invoke-Api $cfg 'GET' '/procs'
        $procs | Sort-Object status, id |
            Format-Table -AutoSize -Property id, status, port |
            Out-String -Width 200 |
            Write-Host
        break
    }

    'ensure' {
        if (-not $Project -or -not $Cmd) { Write-Fail "-Project and -Cmd are required for ensure." }
        $cfg = Require-Supervisor
        $resolvedRoot = Normalize-RootPath (Resolve-Path $Root).Path
        $registry = Get-ProjectsRegistry
        $procs = Invoke-Api $cfg 'GET' '/procs'
        $cmdNorm = ($Cmd -replace '\s+', ' ').Trim()

        # Match project name AND registry root AND cmd - root is what stops a
        # same-named worktree's process from being silently reused (todo 20).
        $match = $null
        foreach ($proc in ($procs | Where-Object { $_.project -eq $Project })) {
            $parts = $proc.id.Split(':', 2)
            $reg = $registry | Where-Object { $_.id -eq $parts[0] } | Select-Object -First 1
            if (-not $reg -or (Normalize-RootPath $reg.root) -ne $resolvedRoot) { continue }
            $regCmd = $reg.commands | Where-Object { $_.id -eq $parts[1] } | Select-Object -First 1
            if ($regCmd -and (($regCmd.cmd -replace '\s+', ' ').Trim()) -eq $cmdNorm) { $match = $proc; break }
        }

        if ($match) {
            if ($match.status -eq 'running') {
                if ($Restart) {
                    if ($match.kind -eq 'flutter') { Invoke-Api $cfg 'POST' "/procs/$($match.id)/reload" | Out-Null }
                    else { Invoke-Api $cfg 'POST' "/procs/$($match.id)/restart" | Out-Null }
                }
            }
            elseif ($match.status -eq 'crashed') {
                Invoke-Api $cfg 'POST' "/procs/$($match.id)/restart" | Out-Null
            }
            else {
                Invoke-Api $cfg 'POST' "/procs/$($match.id)/start" | Out-Null
            }
            $fresh = (Invoke-Api $cfg 'GET' '/procs') | Where-Object { $_.id -eq $match.id }
            Write-Info "$($fresh.id) status=$($fresh.status) port=$($fresh.port)"
            break
        }

        $body = @{ root = (Resolve-Path $Root).Path; cmd = $Cmd; kind = $Kind; use_dynamic_port = (-not $NoDynamicPort) }
        $started = Invoke-Api $cfg 'POST' '/run' $body
        Write-Info "$($started.id) status=$($started.status) port=$($started.port)"
        break
    }

    'logs' {
        if (-not $Id) { Write-Fail "-Id is required for logs." }
        $cfg = Require-Supervisor
        $entries = Invoke-Api $cfg 'GET' "/procs/$Id/logs"
        foreach ($e in $entries) { Write-Host "[$($e.stream)] $($e.text)" }
        break
    }

    'stop' {
        if (-not $Id) { Write-Fail "-Id is required for stop." }
        $cfg = Require-Supervisor
        Invoke-Api $cfg 'POST' "/procs/$Id/stop" | Out-Null
        Write-Info "$Id stopped."
        break
    }

    'restart' {
        if (-not $Id) { Write-Fail "-Id is required for restart." }
        $cfg = Require-Supervisor
        Invoke-Api $cfg 'POST' "/procs/$Id/restart" | Out-Null
        Write-Info "$Id restarted."
        break
    }

    'rm' {
        if (-not $Id) { Write-Fail "-Id is required for rm." }
        $cfg = Require-Supervisor
        Invoke-Api $cfg 'DELETE' "/procs/$Id" | Out-Null
        Write-Info "$Id removed."
        break
    }
}
