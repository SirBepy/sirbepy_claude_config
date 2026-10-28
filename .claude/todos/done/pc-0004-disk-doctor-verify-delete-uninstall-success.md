<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=1, content-hash=483242c8 -->
# disk-doctor delete/uninstall commands must verify actual state, not trust exit codes

**Type:** skill-improvement

## Goal

Document a hard gotcha in `skills/disk-doctor/windows.md`: `Start-Process <installer/uninstaller> -Wait; "DONE X"` reports success even when the launched process did nothing. This burned real time in a 2026-08-05 session - 3 of 4 non-elevated MSI uninstalls silently no-op'd (needs admin rights, `/qn` suppresses the UAC prompt rather than erroring), and one elevated retry also silently failed for the same underlying reason (missed/uncounted UAC click). Every one of them still printed "DONE" and reported exit code 0 to the harness.

## Context

The pattern that failed: `Start-Process msiexec.exe -ArgumentList '/X{GUID}','/qn' -Wait; "DONE App"`. The task-notification layer reports the *script's own* exit code (which succeeds because the script ran fine and printed a string), not the launched process's real exit code - so a silently-failed `msiexec`/uninstaller looks identical to a successful one from the harness's perspective.

The fix used mid-session: after any uninstall/delete command, independently verify via a second, unrelated check - `Test-Path`/`ls` on the actual install folder, and/or a registry re-query (`Get-ItemProperty ... Uninstall\*`) confirming the entry is gone - before reporting success to Joe. Caught the false-positive both times it happened this session.

## Approach

Add a GOTCHA block to `windows.md` (same style as the existing robocopy-exit-code and PowerShell-function-doesn't-persist gotchas):

> GOTCHA: `Start-Process ... -Wait` reports the wrapper script's exit code, not the launched process's. An uninstaller that fails silently (missing elevation, cancelled UAC, locked file) still looks like success. ALWAYS verify independently after any delete/uninstall claim - re-check the file/folder is actually gone (`Test-Path`) and/or the registry Uninstall entry is actually cleared - before telling Joe it's done.

Also worth a one-line addition to the "Output rules" section: "delete/uninstall commands report success only after an independent verification, not from the command's own exit code."

## Acceptance

- windows.md contains this gotcha in a place a future session will actually read before running delete/uninstall commands.
- No behavior change needed elsewhere - this is a documentation/discipline fix, not a new scan step.

## Notes

- 2026-08-08: Added GOTCHA block after the "PowerShell functions don't persist" gotcha (~line 16), and one line to Output rules (~line 87).
