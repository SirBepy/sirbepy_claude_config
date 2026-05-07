---
name: fix-studio-content-folder
description: Triggers on /fix-studio-content-folder only. Repoints HKCU Roblox Studio ContentFolder at a live Versions/version-<hash>/content/ folder when run-in-roblox panics with "system cannot find the file specified" after Roblox auto-prunes old install dirs.
---

# /fix-studio-content-folder

> Repoint Studio's ContentFolder registry key at a live Versions install so run-in-roblox stops panicking.

## When to use

`run-in-roblox` (and any wrapper that uses it, e.g. project `scripts/check.sh`) panics with:

```
thread '<unnamed>' panicked at 'called Result::unwrap() on an Err value: The system cannot find the file specified. (os error 2)', src/main.rs:75:9
[ERROR run_in_roblox] receiving on a closed channel
```

Cause: `HKCU:\Software\Roblox\RobloxStudio\ContentFolder` points at a `Versions\version-<hash>\content/` dir that Roblox auto-pruned on update. Studio only rewrites the key on a full launch, so the stale path lingers.

Windows-only. Writing HKCU needs no elevation.

## Steps

1. List candidate version dirs:
   ```powershell
   Get-ChildItem "$env:LOCALAPPDATA\Roblox\Versions" -Directory
   ```
2. Filter to live Studio installs (must contain BOTH `content\` and `RobloxStudioBeta.exe`). Sort by `LastWriteTime` descending. Pick the most recent.
3. Read current key (for the diff log):
   ```powershell
   (Get-ItemProperty 'HKCU:\Software\Roblox\RobloxStudio' -Name ContentFolder).ContentFolder
   ```
4. Set key to `<picked-dir>\content/` (note trailing forward slash):
   ```powershell
   Set-ItemProperty -Path 'HKCU:\Software\Roblox\RobloxStudio' -Name ContentFolder -Value '<picked>\content/'
   ```
5. Print before/after values and a "Studio does NOT need to restart" reminder. Tell the dev to re-run whatever invoked run-in-roblox (e.g. `scripts/check.sh`).

## Edge cases

- **No version dir has both `content\` and `RobloxStudioBeta.exe`.** Abort and tell the dev to launch Studio once from Roblox Player so it reinstalls a full version dir.
- **Multiple candidates with very close timestamps.** Still pick the newest, but list all candidates in the output so the dev can override if needed.
- **Registry key missing entirely.** Create it with `New-ItemProperty -PropertyType String`.
- **Non-Windows platform.** Abort with a clear "Windows only" message; the bug doesn't apply elsewhere.

## Notes

- Don't restart Studio. The fix takes effect on the next `run-in-roblox` subprocess immediately.
- This is a registry fix, not a verifier. Don't auto-run `scripts/check.sh` after - leave that to the dev (the skill should stay project-agnostic).
- Related: memory `reference_studio_play_solo_blocked` covers the separate auto-F5 plugin gating issue; this skill only handles the run-in-roblox subprocess panic.
