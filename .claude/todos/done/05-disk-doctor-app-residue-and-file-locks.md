<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=1, content-hash=f0e6136f -->
# disk-doctor: document app-uninstall residue pattern and the file-lock retry pattern

**Type:** skill-improvement

## Goal

Two manual steps got repeated 3+ times each during a 2026-08-05 app-uninstall round and should become documented disk-doctor procedure rather than ad-hoc improvisation each time.

## Context

**Pattern 1 - AppData/ProgramData residue after uninstall.** Every one of the ~12 apps uninstalled this session left orphaned data outside its own Program Files folder: `%APPDATA%\<App>`, `%LOCALAPPDATA%\<App>`, and sometimes `C:\ProgramData\<App>` (uninstallers don't touch these by design, in case of reinstall). Found ~1.4G+ this way across Antigravity, Postman, Blackmagic Design, Propellerhead Software - none of it was caught by the uninstall command itself, all of it required a separate manual `find`/`Get-ChildItem` sweep afterward.

**Pattern 2 - locked files blocking a delete.** Three separate deletes failed with "file in use by another process": a leftover `stt-sidecar` python.exe holding a `.venv` open, a Gradle daemon holding `.gradle\caches` open, and (correctly left alone) Android Studio's own main process holding `.gradle\caches` open a second time. The first two were safely killed and the delete retried; the third was NOT killed because it was the actual foreground IDE, not a disposable background daemon - that distinction (kill a daemon/orphan vs. don't kill the user's actual open application) was made ad-hoc each time and should be a documented judgment rule.

## Approach

Add to `windows.md`:

1. A step in the app-uninstall flow: "after uninstalling an app, check `%APPDATA%\<App>`, `%LOCALAPPDATA%\<App>`, and `C:\ProgramData\<App>` for leftover data before considering the uninstall complete - uninstallers don't clear these by design."
2. A GOTCHA/judgment note for locked-file deletes: "`Remove-Item` failing with 'in use by another process' - find the locking process (`Get-Process`/`Get-CimInstance Win32_Process -Filter`), then judge: a background daemon/orphan (Gradle daemon, a stray venv python.exe) is safe to kill and retry; the user's actual foreground application (an IDE's main process) is NOT - skip the delete and report it instead of killing the app out from under them."

## Acceptance

- Both patterns are documented as reusable steps, not just something the acting session improvised.
- The judgment rule (daemon vs. foreground app) is explicit enough that a future session doesn't have to re-derive it from scratch.

## Notes

- 2026-08-08: Added residue-check bullet to Output rules (~line 118) and a locked-file GOTCHA after the Start-Process gotcha (~line 18).
