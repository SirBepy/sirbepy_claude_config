<!-- duplicate-checked: grep for _adb_drive_tmp, FLAG_SECURE, "Out of memory", "secure window" in .claude/todos found nothing -->
# android-drive screenshot crashes on secure windows and can leave its temp PNG on the phone

**Summary:** `skills/android-drive/adb-drive.ps1 screenshot` throws `FromFile ... Out of memory` when the foreground app sets FLAG_SECURE, and nothing guarantees the device-side `/sdcard/_adb_drive_tmp.png` is removed when a step fails.
**Type:** skill-improvement
**Origin:** ai

## Observed (2026-11-05, ObsidianVault phone-cleanup chat e2789b28)

- `powershell -File adb-drive.ps1 screenshot -Serial R5CW70H129T` while Microsoft Authenticator was in front (its "Screen Capture" setting is off, so the window is FLAG_SECURE) printed `/sdcard/_adb_drive_tmp.png: 1 file pulled`, then `Exception calling "FromFile" with "1" argument(s): "Out of memory."` from `Get-PngSize` (line 52, `System.Drawing.Image.FromFile`). That is GDI+'s message for an empty or invalid image file, not real memory pressure.
- The chat removed `/sdcard/_adb_drive_tmp.png` by hand afterwards. That matters here: a file left in `/sdcard` is user storage, so a concurrent backup pull or a verify pass of that phone picks it up as a real file.
- A 0-byte or invalid `adb-*.png` was left in `.for_bepy/screenshots/<id>/`.

## Approach

In `Take-Screenshot` (`adb-drive.ps1` around line 121):
1. Write the device temp file to `/data/local/tmp/` instead of `/sdcard/`, so it never lands in user storage that backups read.
2. Remove the device temp file in a `finally`, so a failed pull or parse still cleans up.
3. Before calling `Get-PngSize`, check the pulled file is non-empty and starts with the PNG signature (`89 50 4E 47`). If not, throw a clear error such as "screencap returned no image: the foreground window is probably FLAG_SECURE; use uiautomator dump to read it instead", and delete the bad local file.
4. Add one line to `SKILL.md` Gotchas: secure windows (authenticators, banking apps) give no screenshot, read them with `uiautomator dump`.

Verify: run `screenshot` against an app with FLAG_SECURE on a connected device, and confirm the clear error, no file under `/sdcard/`, and no bad PNG left locally.


## Notes

- fixed: device temp moved to /data/local/tmp, removed in finally, PNG signature check before Get-PngSize, SKILL.md gotcha added; tests in skills/android-drive/test_adb_drive.ps1 (stubbed adb, red on the old script). Live FLAG_SECURE check on a phone: verify only, no device attached tonight.