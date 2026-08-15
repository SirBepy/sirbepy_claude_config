# disk-doctor — Windows platform file

Repeatable cleanup scan for Joe's PC (win32, Windows 11). You **advise**, never delete. Joe runs the delete commands. You may run the read-only **scan** commands yourself; you never run `Remove-Item` / `Clear-RecycleBin` / `cleanmgr` / `docker prune`.

## Sizing helper (robocopy, not Get-ChildItem -Recurse)

Directory sizes use `robocopy` in list-only mode, NOT `Get-ChildItem -Recurse`. Reasons (all verified on this machine 2026-06-03):
- **Speed:** robocopy sized the full home tree in ~32s; the recursive `Get-ChildItem` version hung past 2 minutes and had to be killed.
- **Junctions:** `/XJ` skips junction points, so it never loops through the reparse points scattered across `AppData`.
- **`robocopy` ships with Windows** - no external tool to install (WizTree/TreeSize not present here).

GOTCHA: robocopy exits with code 1-7 on SUCCESS (1 = "files found"). The harness/PowerShell will surface "Exit code 1" even though the scan worked - that is normal, not an error. Only exit code ≥ 8 is a real failure.

GOTCHA: PowerShell functions do NOT persist between separate tool calls, so each sizing command below **embeds** this helper inline. When running them yourself, paste the whole block, not just the pipeline.

GOTCHA: `Start-Process ... -Wait` reports the wrapper script's exit code, not the launched process's. An uninstaller that fails silently (missing elevation, cancelled UAC, locked file) still looks like success. ALWAYS verify independently after any delete/uninstall claim - re-check the file/folder is actually gone (`Test-Path`) and/or the registry Uninstall entry is actually cleared - before telling Joe it's done.

GOTCHA: `Remove-Item` failing with "in use by another process" - find the locking process (`Get-CimInstance Win32_Process -Filter "..."` or `Get-Process`), then judge: a background daemon/orphan (Gradle daemon, a stray venv `python.exe`) is safe to kill and retry; the user's actual foreground application (an IDE's main process) is NOT - skip the delete and report it instead of killing the app out from under them.

```powershell
function Get-DirGB($p){ $o=robocopy $p NULL /L /S /NJH /NFL /NDL /BYTES /XJ /R:0 /W:0; $l=@($o|Where-Object{$_ -match '^\s*Bytes :'})[0]; if($l -and $l -match 'Bytes :\s+(\d+)'){[math]::Round([int64]$Matches[1]/1GB,2)}else{0} }
```

## How to run a scan

**Dispatch, don't run inline.** Send the scan commands for this round to a `general-purpose` subagent,
`model: sonnet`, prompted to run the listed PowerShell blocks and return only a digested summary
(dirs/caches over ~1GB with sizes) - never raw robocopy table dumps into the main thread. One subagent
call per round (initial sweep, then a separate one per drill-down round) keeps the back-and-forth
Joe-steered without a monolithic report.

Run these (PowerShell), then rank findings by payoff (GB freed × ease × reversibility). All read-only.

```powershell
Get-Volume C | Select-Object DriveLetter, @{n='FreeGB';e={[math]::Round($_.SizeRemaining/1GB,1)}}, @{n='TotalGB';e={[math]::Round($_.Size/1GB,1)}}
```
```powershell
# Home top dirs
function Get-DirGB($p){ $o=robocopy $p NULL /L /S /NJH /NFL /NDL /BYTES /XJ /R:0 /W:0; $l=@($o|Where-Object{$_ -match '^\s*Bytes :'})[0]; if($l -and $l -match 'Bytes :\s+(\d+)'){[math]::Round([int64]$Matches[1]/1GB,2)}else{0} }
Get-ChildItem $env:USERPROFILE -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object { [PSCustomObject]@{ GB=(Get-DirGB $_.FullName); Dir=$_.Name } } | Sort-Object GB -Descending | Select-Object -First 12
```
```powershell
# LocalAppData top dirs - biggest Windows blind spot (caches, package stores, app data)
function Get-DirGB($p){ $o=robocopy $p NULL /L /S /NJH /NFL /NDL /BYTES /XJ /R:0 /W:0; $l=@($o|Where-Object{$_ -match '^\s*Bytes :'})[0]; if($l -and $l -match 'Bytes :\s+(\d+)'){[math]::Round([int64]$Matches[1]/1GB,2)}else{0} }
Get-ChildItem $env:LOCALAPPDATA -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object { [PSCustomObject]@{ GB=(Get-DirGB $_.FullName); Dir=$_.Name } } | Sort-Object GB -Descending | Select-Object -First 12
```
```powershell
# Temp + Recycle Bin
[PSCustomObject]@{ TempGB=[math]::Round((Get-ChildItem $env:TEMP -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum/1GB,2); RecycleGB=[math]::Round((((New-Object -ComObject Shell.Application).Namespace(0xA).Items() | Measure-Object Size -Sum).Sum)/1GB,2) }
```
```powershell
# Stale node_modules (depth-capped to keep it fast)
function Get-DirGB($p){ $o=robocopy $p NULL /L /S /NJH /NFL /NDL /BYTES /XJ /R:0 /W:0; $l=@($o|Where-Object{$_ -match '^\s*Bytes :'})[0]; if($l -and $l -match 'Bytes :\s+(\d+)'){[math]::Round([int64]$Matches[1]/1GB,2)}else{0} }
Get-ChildItem $env:USERPROFILE -Directory -Recurse -Depth 5 -Filter node_modules -Force -ErrorAction SilentlyContinue | ForEach-Object { [PSCustomObject]@{ GB=(Get-DirGB $_.FullName); Path=$_.FullName.Replace($env:USERPROFILE,'~') } } | Sort-Object GB -Descending | Select-Object -First 10
```
```powershell
# Build-artifact sweep across every repo - MANDATORY, not optional. On 2026-07-19 this single
# step found 150GB+ (Rust `target` dirs left over from switched CARGO_TARGET_DIR configs, Flutter
# `build`/.dart_tool, Python venv/.venv) - bigger than every other scan step in this file combined.
# Scans the full user profile (mirrors the node_modules sweep above) instead of a hand-maintained
# root list - a mandatory step shouldn't depend on remembering which dev roots exist.
function Get-DirGB($p){ $o=robocopy $p NULL /L /S /NJH /NFL /NDL /BYTES /XJ /R:0 /W:0; $l=@($o|Where-Object{$_ -match '^\s*Bytes :'})[0]; if($l -and $l -match 'Bytes :\s+(\d+)'){[math]::Round([int64]$Matches[1]/1GB,2)}else{0} }
$names = @('target','build','.dart_tool','dist','.venv','venv')
Get-ChildItem $env:USERPROFILE -Directory -Recurse -Depth 6 -Force -ErrorAction SilentlyContinue | Where-Object { $names -contains $_.Name } | ForEach-Object { [PSCustomObject]@{ GB=(Get-DirGB $_.FullName); Path=$_.FullName.Replace($env:USERPROFILE,'~') } } | Sort-Object GB -Descending | Select-Object -First 25
```
```powershell
# Screenshot session folders across all repos - /close (todo 324) no longer deletes these itself,
# so they only age out here. Flags anything over 30 days (a closed chat's shots have no further use).
$cutoffDays = 30
Get-ChildItem $env:USERPROFILE -Directory -Recurse -Depth 6 -Force -ErrorAction SilentlyContinue | Where-Object { $_.FullName -match '\\\.for_bepy\\screenshots$' } | ForEach-Object {
  $root = $_.FullName
  Get-ChildItem $root -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $mb = if ($_.PSIsContainer) { [math]::Round(((Get-ChildItem $_.FullName -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum)/1MB,1) } else { [math]::Round($_.Length/1MB,1) }
    $ageDays = [math]::Round((New-TimeSpan -Start $_.LastWriteTime -End (Get-Date)).TotalDays,0)
    [PSCustomObject]@{ Repo=$root; Item=$_.Name; MB=$mb; AgeDays=$ageDays; Stale=($ageDays -gt $cutoffDays) }
  }
} | Sort-Object AgeDays -Descending
```
```powershell
# Package-manager caches (correct bases: cargo/gradle live under USERPROFILE, the rest under LOCALAPPDATA)
function Get-DirGB($p){ $o=robocopy $p NULL /L /S /NJH /NFL /NDL /BYTES /XJ /R:0 /W:0; $l=@($o|Where-Object{$_ -match '^\s*Bytes :'})[0]; if($l -and $l -match 'Bytes :\s+(\d+)'){[math]::Round([int64]$Matches[1]/1GB,2)}else{0} }
@(
  @{N='gradle';     P=(Join-Path $env:USERPROFILE '.gradle')},
  @{N='cargo';      P=(Join-Path $env:USERPROFILE '.cargo')},
  @{N='npm-cache';  P=(Join-Path $env:LOCALAPPDATA 'npm-cache')},
  @{N='pnpm-store'; P=(Join-Path $env:LOCALAPPDATA 'pnpm')},
  @{N='pip';        P=(Join-Path $env:LOCALAPPDATA 'pip\Cache')}
) | ForEach-Object { if(Test-Path $_.P){ [PSCustomObject]@{ GB=(Get-DirGB $_.P); Cache=$_.N } } } | Sort-Object GB -Descending
```
```powershell
# C: top level + Program Files one-level-deep - MANDATORY. The USERPROFILE-scoped steps above
# structurally cannot see Steam/Battle.net/most desktop apps, which live under Program Files.
function Get-DirGB($p){ $o=robocopy $p NULL /L /S /NJH /NFL /NDL /BYTES /XJ /R:0 /W:0; $l=@($o|Where-Object{$_ -match '^\s*Bytes :'})[0]; if($l -and $l -match 'Bytes :\s+(\d+)'){[math]::Round([int64]$Matches[1]/1GB,2)}else{0} }
Get-ChildItem C:\ -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object { [PSCustomObject]@{ GB=(Get-DirGB $_.FullName); Dir=$_.Name } } | Sort-Object GB -Descending
@('C:\Program Files','C:\Program Files (x86)') | ForEach-Object { $base=$_; Get-ChildItem $base -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object { [PSCustomObject]@{ GB=(Get-DirGB $_.FullName); Dir="$base\$($_.Name)" } } } | Sort-Object GB -Descending | Select-Object -First 15
```
```powershell
# Steam/Battle.net game libraries - libraryfolders.vdf lists every library path, not just the default
$vdf = 'C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf'
if (Test-Path $vdf) {
  function Get-DirGB($p){ $o=robocopy $p NULL /L /S /NJH /NFL /NDL /BYTES /XJ /R:0 /W:0; $l=@($o|Where-Object{$_ -match '^\s*Bytes :'})[0]; if($l -and $l -match 'Bytes :\s+(\d+)'){[math]::Round([int64]$Matches[1]/1GB,2)}else{0} }
  $libs = (Get-Content $vdf | Select-String '"path"\s+"([^"]+)"').Matches | ForEach-Object { $_.Groups[1].Value -replace '\\\\','\' }
  $libs | ForEach-Object { $common = Join-Path $_ 'steamapps\common'; if (Test-Path $common) { Get-ChildItem $common -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object { [PSCustomObject]@{ GB=(Get-DirGB $_.FullName); Game=$_.Name } } } } | Sort-Object GB -Descending
}
# Battle.net has no equivalent manifest - check its default install dir directly if present
```
```powershell
# Windows-overhead context numbers - REPORT ONLY, never delete candidates (see NEVER-TOUCH)
function Get-DirGB($p){ $o=robocopy $p NULL /L /S /NJH /NFL /NDL /BYTES /XJ /R:0 /W:0; $l=@($o|Where-Object{$_ -match '^\s*Bytes :'})[0]; if($l -and $l -match 'Bytes :\s+(\d+)'){[math]::Round([int64]$Matches[1]/1GB,2)}else{0} }
[PSCustomObject]@{
  WinSxSGB   = Get-DirGB 'C:\Windows\WinSxS'
  HiberfilGB = if (Test-Path 'C:\hiberfil.sys') { [math]::Round((Get-Item 'C:\hiberfil.sys' -Force).Length/1GB,2) } else { 0 }
  PagefileGB = if (Test-Path 'C:\pagefile.sys') { [math]::Round((Get-Item 'C:\pagefile.sys' -Force).Length/1GB,2) } else { 0 }
  WindowsOld = Test-Path 'C:\Windows.old'
}
```

### Second-pass drill-down

After the initial scan, drill into the **top-3 dirs (home or LocalAppData) exceeding 2GB**:

```powershell
function Get-DirGB($p){ $o=robocopy $p NULL /L /S /NJH /NFL /NDL /BYTES /XJ /R:0 /W:0; $l=@($o|Where-Object{$_ -match '^\s*Bytes :'})[0]; if($l -and $l -match 'Bytes :\s+(\d+)'){[math]::Round([int64]$Matches[1]/1GB,2)}else{0} }
Get-ChildItem '<dir>' -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object { [PSCustomObject]@{ GB=(Get-DirGB $_.FullName); Dir=$_.Name } } | Sort-Object GB -Descending | Select-Object -First 10
```

Hard cap: 3 dirs max regardless of how many exceed the threshold.

## Output rules

- Rank deletables, biggest realistic win first.
- Per item: size, what it is, regenerates/re-downloadable?, exact delete command (PowerShell `Remove-Item -Recurse -Force` or the named cleanup command).
- Prefer the **native/owner cleanup** over raw deletes: `docker system prune` for Docker, `cleanmgr`/Storage Sense for Windows Update leftovers / Windows.old / Delivery Optimization, `npm cache clean --force` / `pnpm store prune` for package caches. Never raw-`Remove-Item` inside `C:\Windows\*`.
- Flag slow-to-restore items - confirm live project targets before swinging (e.g. node_modules in an active repo).
- Never suggest anything in NEVER-TOUCH below.
- Offer to write commands; Joe runs them. You never run the delete.
- Delete/uninstall commands report success only after independent verification, never on the command's own exit code.
- After uninstalling an app, check `%APPDATA%\<App>`, `%LOCALAPPDATA%\<App>`, and `C:\ProgramData\<App>` for leftover data before considering the uninstall complete - uninstallers don't clear these by design.

## Self-improvement (only when invoked as /disk-doctor)

At END of scan, propose any new KNOWN-SAFE spots, NEVER-TOUCH additions, or a SCAN LOG entry using the confirmation gate in `gate.md` (in this skill folder). Only edit this file when invoked as `/disk-doctor`. No silent/auto edits, no edits when triggered indirectly.

---

## NEVER-TOUCH (Joe's machine)

- `~/.claude/` - config, skills, memory.
- `~/.ssh/` + any `*.jks` / `*.pem` / `*.key` keystores - signing & SSH keys.
- `~/fvm` (~13G) - active Flutter toolchains, not junk.
- `~/.gitconfig`, credential stores.
- `C:\Windows\WinSxS` - component store. Deleting corrupts the OS; only DISM may clean it.
- `pagefile.sys`, `hiberfil.sys`, `swapfile.sys` - system-managed; never manual-delete (disable the feature instead if reclaiming).
- `C:\Windows\System32`, `C:\Program Files*`, `C:\ProgramData` package installs - not cleanup targets.

## KNOWN SAFE-TO-DELETE (regenerates / re-downloadable)

- Gradle cache `~/.gradle\caches` (~16G here, the biggest single win) - re-downloads on next build.
- npm cache - `npm cache clean --force` (~4G). pnpm store - `pnpm store prune`. cargo registry `~/.cargo\registry` - re-downloads. pip cache - `pip cache purge`.
- Docker: `docker system prune -a` (images/build cache; LocalAppData\Docker was ~15G here) - re-pulls. Confirm no needed images first.
- `$env:TEMP\*` and `$env:LOCALAPPDATA\Temp\*` - temp files, regenerate. `Get-ChildItem $env:TEMP -Force | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue` (in-use files skip).
- Recycle Bin - `Clear-RecycleBin -Force`.
- Browser caches under `$env:LOCALAPPDATA\<Browser>\User Data\*\Cache` - regenerate.
- Stale-project `node_modules` - `npm i` / `pnpm i` rebuilds. Build artifacts (`build/`, `.dart_tool/`, `dist/`, `.next/`, `target/`, `venv/`, `.venv/`) - regenerate. The build-artifact sweep step above is the biggest single win found so far (150G+ on 2026-07-19) - always run it, don't skip as optional.
- Windows Update leftovers / `Windows.old` / Delivery Optimization - via `cleanmgr` or Storage Sense, not manual delete.
- `.for_bepy/screenshots/` subfolders and loose legacy files older than 30 days - throwaway per-chat verification shots; `/close` stopped deleting these (todo 324), so they only clear here. Report per-repo, oldest first; never touch `.portfolio-data/` (portfolio keepers, separate scope).

## KNOWN HARD (judgment call, not a routine safe-delete)

- Docker Desktop's `docker_data.vhdx` (`LocalAppData\Docker\wsl\disk\`) does NOT shrink via `docker system prune` alone, nor via `wsl --shutdown` + `diskpart compact vdisk` alone (0 bytes reclaimed in practice - no TRIM occurred). The disk only mounts while `dockerd` itself is running, so `fstrim` from an external WSL distro can't reach it once Docker Desktop is stopped. The only operation that reliably reclaims the space is deleting the VHDX and letting Docker Desktop recreate it fresh - but this destroys any named Docker volumes not already checked for. Treat as a judgment call requiring an explicit volumes-check (`docker volume ls` + confirm none hold real data) before ever proposing the delete-and-recreate path, never bundled into a "just compact it" recommendation.

## SCAN LOG

Cap: 5 entries max. When at cap, drop the entry with the earliest date field before appending; if dates tie, drop the topmost entry. Never reorder remaining entries.

- 2026-06-03: First Windows scan. C: free 24.3/930.6G (tight). Home top: Desktop 288.6G, AppData 197.5G, Videos 40G, Downloads 34.3G, .gradle 16.3G, fvm 13.2G. LocalAppData: Packages 20G, Android 15.7G, Docker 14.9G, Google 13.7G. Caches: gradle 16.3G, npm 4.2G, cargo 2.5G. Temp 0.56G, Recycle 0.79G. Top safe wins: gradle cache + Docker prune + npm cache ≈ 35G.
- 2026-07-19: Deep Windows scan (supersedes 2026-06-03 data). C: free 29.6/930.6G. Added mandatory build-artifact sweep step - found 150G+ across 19 repos in Desktop\Projects (biggest: claude_usage_in_taskbar 90.6G in 3 duplicate src-tauri target dirs from switched CARGO_TARGET_DIR configs, server_supervisor 12.1G, pomodoro-overlay 8.5G, odysseus 13.2G target+venv, revaire-mobile 6.7G build+.dart_tool, 12 more repos 0.5-3G each). Root cause found and fixed: global ~/.cargo/config.toml had no target-dir set, so one-off manual overrides never stuck - added `target-dir = "D:/cargo-target"` globally so this stops recurring. Other safe wins: Docker 26.5G, gradle 19.5G, LocalAppData Temp 17.5G, npm/pip/cargo/pnpm/playwright/recycle ~15G, huggingface hub 60.2G (cleared, unused models), stale node_modules 10 repos ~4G. Judgment calls (Joe's call each time, not auto-safe): game data (PrismLauncher instance 33.4G - Joe approved delete, curseforge 5.3G - kept), Android AVD image 11.6G, ollama models 7.7G idle 6-7wk (Joe kept), Roblox project folders misfiled in Downloads 30.4G (moved to D:\RobloxDev not deleted). Windows-level bloat (SoftwareDistribution, Windows.old) checked clean - not a Windows problem this time. Non-cache real data generally needs a judgment-call question - cache/build-artifact patterns don't.
- 2026-08-05: Follow-up scan. C: free 127.8/930.6G (recovered from June's 24-30G). Confirmed claude_usage_in_taskbar's Tauri junk was NOT actively regrowing - all found Rust target dirs (claude_usage_in_taskbar target 19.95G+src-tauri/target 14.93G+target-alt 16.47G, server_supervisor src-tauri/target 12.05G, odysseus desktop/src-tauri/target 9.42G) predate the 2026-07-19 global target-dir fix and were simply never cleaned up. Found + fixed 2 live issues: (1) claude_usage_in_taskbar's settings.local.json (+worktree copy) had 3 pre-approved permissions hardcoding CARGO_TARGET_DIR=src-tauri/target-export, bypassing the global redirect if ever reused - removed. (2) shared unnamespaced D:/cargo-target meant unrelated projects/tools (Claude Conductor build, cargo-audit) already landed in the same debug/release folders - added per-project target-dir overrides (own D: subfolder) to claude_usage_in_taskbar, server_supervisor, pomodoro-overlay, odysseus .cargo/config.toml. Also found D: itself had ~33.6G of stale one-off pre-fix test folders (claude_usage_in_taskbar__src-tauri 18G, server_supervisor__src-tauri 8.9G, pomodoro-overlay__src-tauri 6.7G) - junk isn't C:-only, D: needs the same recurring check. Other wins: Docker 26.5G, npm-cache 7.65G, gradle 4.48G, LocalAppData Temp 19.64G, playwright caches 8.44G, pip 2.51G, revaire-mobile build+.dart_tool 6.7G, odysseus venv 3.8G, llama.cpp build 1.07G. Total addressable ~192G across C: and D:. Judgment calls (kept, not junk): Roblox LocalAppData cache 6.87G, .screenpipe 27.02G.
