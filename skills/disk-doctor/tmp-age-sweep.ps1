<#
.SYNOPSIS
  Lists (default) or deletes (-Apply) top-level C:\tmp items whose newest file is older than -Days.

.DESCRIPTION
  Joe runs this himself: the Claude Code harness refuses any Remove-Item naming a drive-root
  child, so Claude hands over the absolute-path invocation instead of deleting.

  ONE recursive pass over the tree finds every item's newest LastWriteTime. A hand-rolled .NET walk
  replaces Get-ChildItem -Recurse because Windows PowerShell 5.1 follows directory junctions and
  symlinks (pnpm node_modules are full of them), which double-walks other trees and lets a target's
  mtime leak into the item. Reparse points are never entered, here or while deleting; a junction is
  removed as a link and its target survives.

  An item with ANY file newer than the cutoff is never listed. Empty directories use their own
  mtime. Keep-list defaults mirror NEVER-TOUCH in windows.md; extend them with -Keep.

  Preview is the default. -Apply deletes. Any -Root other than C:\tmp is refused (exit 2).

.PARAMETER Days
  Age cutoff in days, measured on the newest file inside each top-level item. Default 21.

.PARAMETER Keep
  Extra top-level names or -like globs to leave alone, added to the built-in keep-list.

.PARAMETER Apply
  Actually delete. Without it nothing is touched.

.PARAMETER Root
  Must resolve to C:\tmp. Exists so the refusal is testable, not to sweep other trees.
#>
[CmdletBinding()]
param(
    [int]$Days = 21,
    [string[]]$Keep = @(),
    [switch]$Apply,
    [string]$Root = 'C:\tmp'
)

$script:DefaultKeep = @('salvage', 'memory-backup-*', '*.java', '*.java.bak', 'sftp-*', 'live-*.yml', 'n8n-db.sqlite')
# cc-target is a Rust target dir Joe keeps rebuilding; deleting a live one only costs a rebuild,
# so it needs 21 idle days no matter how small -Days is.
$script:MinDaysByName = @{ 'cc-target' = 21 }

function Assert-SweepRoot([string]$Path, [string]$Allowed = 'C:\tmp') {
    # Returns the normalised root, or $null when it is not exactly the allowed root.
    try { $full = [System.IO.Path]::GetFullPath($Path).TrimEnd('\') } catch { return $null }
    if ($full -ieq $Allowed.TrimEnd('\')) { return $full }
    return $null
}

function Test-Reparse([System.IO.FileSystemInfo]$Info) {
    return (($Info.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
}

function Get-TreeStats([string]$Path) {
    # Newest file mtime and total bytes under a directory, never entering reparse points.
    $newest = [datetime]::MinValue
    $bytes = [int64]0
    $files = 0
    $stack = New-Object System.Collections.Generic.Stack[string]
    $stack.Push($Path)
    while ($stack.Count -gt 0) {
        $dir = $stack.Pop()
        try { $entries = (New-Object System.IO.DirectoryInfo ('\\?\' + $dir)).GetFileSystemInfos() }
        catch { continue }
        foreach ($e in $entries) {
            if ($e -is [System.IO.DirectoryInfo]) {
                if (-not (Test-Reparse $e)) { $stack.Push($e.FullName.Replace('\\?\', '')) }
            }
            else {
                $files++
                if ($e.LastWriteTime -gt $newest) { $newest = $e.LastWriteTime }
                try { $bytes += $e.Length } catch { }
            }
        }
    }
    return [pscustomobject]@{ Newest = $newest; Bytes = $bytes; Files = $files }
}

function Get-TmpSweepPlan {
    param([string]$Root, [int]$Days, [string[]]$KeepList, [datetime]$Now = (Get-Date))
    $items = Get-ChildItem -LiteralPath $Root -Force -ErrorAction SilentlyContinue
    $result = New-Object System.Collections.Generic.List[object]
    foreach ($it in $items) {
        $name = $it.Name
        $kept = $false
        foreach ($k in $KeepList) { if ($name -like $k) { $kept = $true; break } }
        if ($kept) { continue }

        $effectiveDays = $Days
        if ($script:MinDaysByName.ContainsKey($name) -and $script:MinDaysByName[$name] -gt $effectiveDays) {
            $effectiveDays = $script:MinDaysByName[$name]
        }
        $cutoff = $Now.AddDays(-$effectiveDays)

        if ($it -is [System.IO.DirectoryInfo] -and -not (Test-Reparse $it)) {
            $s = Get-TreeStats $it.FullName
            $newest = $s.Newest
            # The dir's own mtime also counts: it is the only signal for an empty dir, and it
            # moves when an entry is added or removed, which is recent activity worth keeping.
            if ($it.LastWriteTime -gt $newest) { $newest = $it.LastWriteTime }
            $bytes = $s.Bytes
        }
        else {
            $newest = $it.LastWriteTime
            $bytes = 0
            if ($it -is [System.IO.FileInfo]) { try { $bytes = $it.Length } catch { } }
        }

        if ($newest -lt $cutoff) {
            $result.Add([pscustomobject]@{
                    Name    = $name
                    Path    = $it.FullName
                    Newest  = $newest
                    Bytes   = $bytes
                    IsLink  = (Test-Reparse $it)
                    IsDir   = ($it -is [System.IO.DirectoryInfo])
                })
        }
    }
    return , $result.ToArray()
}

function Remove-TreeSafe([string]$Path) {
    # Deletes a tree without following reparse points: a junction or symlink is unlinked, its
    # target is left alone (Windows PowerShell 5.1 Remove-Item -Recurse can follow them).
    $long = '\\?\' + $Path
    $info = New-Object System.IO.DirectoryInfo $long
    if (-not $info.Exists) {
        $f = New-Object System.IO.FileInfo $long
        if ($f.Exists) { $f.Attributes = [System.IO.FileAttributes]::Normal; $f.Delete() }
        return
    }
    if (Test-Reparse $info) { $info.Delete(); return }
    foreach ($e in $info.GetFileSystemInfos()) {
        $child = $e.FullName.Replace('\\?\', '')
        Remove-TreeSafe $child
    }
    $info.Attributes = [System.IO.FileAttributes]::Directory
    $info.Delete()
}

function Invoke-TmpSweep {
    param([string]$Root, [int]$Days, [string[]]$KeepList, [bool]$Apply)
    $plan = Get-TmpSweepPlan -Root $Root -Days $Days -KeepList $KeepList
    $total = [int64]0
    foreach ($p in ($plan | Sort-Object Bytes -Descending)) {
        $total += $p.Bytes
        $gb = '{0,8:N2} GB' -f ($p.Bytes / 1GB)
        Write-Host ("{0}  {1:yyyy-MM-dd}  {2}" -f $gb, $p.Newest, $p.Name)
    }
    Write-Host ("{0} item(s), {1:N2} GB older than {2} days under {3}" -f $plan.Count, ($total / 1GB), $Days, $Root)
    if (-not $Apply) {
        Write-Host 'Preview only, nothing deleted. Re-run with -Apply to delete the items above.'
        return $plan
    }
    foreach ($p in $plan) {
        try { Remove-TreeSafe $p.Path }
        catch { Write-Host ("FAILED  {0}: {1}" -f $p.Name, $_.Exception.Message) }
    }
    Write-Host 'Done.'
    return $plan
}

# Dot-sourcing (the test does this) loads the functions without running the sweep.
if ($MyInvocation.InvocationName -ne '.') {
    $rootFull = Assert-SweepRoot $Root
    if (-not $rootFull) {
        Write-Host "Refusing root '$Root': this script only sweeps C:\tmp."
        exit 2
    }
    if (-not (Test-Path -LiteralPath $rootFull)) {
        Write-Host "$rootFull does not exist, nothing to sweep."
        exit 0
    }
    $null = Invoke-TmpSweep -Root $rootFull -Days $Days -KeepList ($script:DefaultKeep + $Keep) -Apply:$Apply.IsPresent
}
