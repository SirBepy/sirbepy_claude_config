<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-0349 is the landscape coordinate bug, this is serial resolution -->
# adb-drive picks device "e" when one device is attached and no -Serial is given

**Type:** skill-improvement
**Origin:** ai
**Summary:** The android-drive script fails with "device 'e' not found" unless -Serial is passed, even with a single emulator attached.

## Goal

Calling `adb-drive.ps1` with no `-Serial` works when exactly one device is attached.

## Context

- `skills/android-drive/adb-drive.ps1`, function `Resolve-Serial`, does `$ids = $lines | ForEach-Object {...}` and `return $ids[0]`. With one device, PowerShell unwraps the pipeline result to a plain string, so `$ids[0]` is its first character: `e` from `emulator-5554`.
- Seen 2026-11-04 in zng-biller: `screenshot` printed `adb.exe: device 'e' not found`; the same call with `-Serial emulator-5554` worked.

## Approach

Wrap in an array: `$ids = @($lines | ForEach-Object { ($_ -split "`t")[0] })`.

## Acceptance

- With one attached device, `adb-drive.ps1 devices` and `screenshot` with no `-Serial` target that device.
- With two devices and no `-Serial`, it still throws its "Multiple devices" error.
