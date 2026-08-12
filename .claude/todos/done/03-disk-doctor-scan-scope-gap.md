<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=1, content-hash=d235e44b -->
# disk-doctor scans miss Program Files, ProgramData, Windows, and the Steam/Battle.net game libraries

**Type:** skill-improvement

## Goal

`skills/disk-doctor/windows.md`'s scan commands are all scoped to `$env:USERPROFILE` (home dir + LocalAppData). A 2026-08-05 session ran a full manual top-level `C:\` breakdown afterward and found ~285G that no disk-doctor scan step had ever touched: `Program Files (x86)` 134.17G (mostly Steam 66.95G + standalone Warcraft III 28.61G + Heroes of the Storm 18.65G), `Program Files` 21.15G, `ProgramData` 12.09G, `C:\tmp` 22.71G (dev-tooling scratch, outside the home dir), plus the Windows-overhead context numbers (WinSxS, hiberfil.sys, pagefile.sys) that were never reported at all.

## Context

The existing scan steps (home top dirs, LocalAppData top dirs, build-artifact sweep, package caches) all start from `$env:USERPROFILE`. Steam/Battle.net game installs and most standalone desktop apps live under `C:\Program Files` / `C:\Program Files (x86)`, never under the user profile, so the current scan structurally cannot see them. `C:\tmp` (or any top-level non-standard folder) is also invisible for the same reason.

Found via two ad-hoc subagent investigations this session (not part of the disk-doctor skill itself) that had to be hand-written from scratch to cover this ground - see the 2026-08-05 SCAN LOG entry in `windows.md` for the numbers this produced.

## Approach

Add a new mandatory scan step to `windows.md`, alongside the existing "Home top dirs" / "LocalAppData top dirs" steps:

- Size every top-level `C:\` folder (same `Get-DirGB` robocopy function, same table format).
- One level deep into `Program Files` and `Program Files (x86)`.
- Steam library total: find `C:\Program Files (x86)\Steam\steamapps\libraryfolders.vdf`, sum `steamapps\common`, list each installed game with size (also check for a second library folder on another drive, not just the default). Same idea for Battle.net if a separate library exists.
- Windows-overhead context numbers (WinSxS, hiberfil.sys, pagefile.sys, `Windows.old` presence) - report-only, add to NEVER-TOUCH reasoning, never a delete candidate.

## Acceptance

- A fresh `/disk-doctor` run surfaces Program Files/ProgramData/Windows/game-library sizes without needing an ad-hoc subagent dispatch to cover them.
- Existing NEVER-TOUCH / KNOWN-SAFE sections stay accurate - new step is read-only sizing, not a new delete category by itself.

## Notes

Don't fold Steam/game judgment calls into KNOWN-SAFE - games found this way are still a per-title judgment call (see the existing "Judgment calls" pattern in the SCAN LOG), just make sure they're actually *found* by the routine scan instead of requiring a manual dispatch each time.

- 2026-08-08: Added mandatory scan step after the package-cache block (windows.md ~line 67-91) covering C:\ top-level sizing, one-level-deep Program Files/(x86), Steam library.vdf-based game sizing (multi-library aware), and WinSxS/hiberfil/pagefile as report-only context.
