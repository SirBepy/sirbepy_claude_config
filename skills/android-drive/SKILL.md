---
name: android-drive
description: Drives an installed Android app via adb: tap, type, screenshot. For test-on-device or tap-through asks. Not Flutter web (/flutter-e2e) or Patrol.
---

# android-drive

> Stop re-deriving the adb tap/screenshot/inspect loop by hand. The loop was hand-rolled
> roughly 20 times in one session on 2026-08-12, with the same avoidable mistakes recurring
> inside that single session - this skill exists to structurally prevent those, not just
> document them.

## Script, not inline shell

All adb work goes through `adb-drive.ps1` (next to this file):
```
powershell -File "C:/Users/tecno/.claude/skills/android-drive/adb-drive.ps1" <action> [params]
```
Never hand-type the raw adb calls below - the script encodes the two gotchas that bit this
skill's predecessor sessions hardest (see Gotchas), and a bare `$0` or similar in this markdown
body would get clobbered by skill-argument substitution rather than reaching adb.

## Step 0 - resolve the device

Run `devices` first whenever more than one device might be attached (a physical phone plugged in
alongside the emulator is common on this machine):
```
powershell -File adb-drive.ps1 devices
```
If more than one shows `device` status, every subsequent call MUST carry `-Serial <id>` - the
script refuses to guess and throws rather than silently picking one. Never omit `-Serial` "because
there's probably only one" - confirm with `devices` first.

## Step 1 - boot the emulator (skip for a physical device)

The emulator process is long-lived, so start it through `/supervised-run` (kind `generic`), never
a bare `Start-Process`:
```
emulator.exe -avd <name> -no-snapshot-load
```
Then poll for boot completion with the script, not a hand-written loop:
```
powershell -File adb-drive.ps1 wait-boot -Serial <id> -TimeoutSec 120
```

## Step 2 - the drive loop

For every action on screen: **screenshot first, decide, then tap** - never tap against a screen
you haven't just seen render. Read the PNG back before picking coordinates.

1. `screenshot -Serial <id> [-Out <path>]` - screencaps, pulls, deletes the device-side temp file,
   and prints `pngSize=`/`wmSize=`/`scaleX=`/`scaleY=` so you always know the live scale factor.
   Read the returned path with the Read tool before choosing a tap target.
2. Pick X/Y directly off the pixels you just read (that screenshot's own coordinate space).
3. `tap-and-capture -Serial <id> -X <x> -Y <y> -RefShot <path-from-step-1> [-WaitMs 800] [-Out <path>]`
   - converts your X/Y from the screenshot's pixel space into the space `input tap` actually
   expects, taps, waits, and takes a fresh screenshot so you see the result of your own action
   without a second round trip. Read the returned `after=` path before deciding the next step.
4. Repeat from 1 for the next screen.

Use bare `tap` (no post-tap screenshot) only for a rapid sequence where you already know you'll
screenshot again in a step or two - default to `tap-and-capture`.

## Text fields

Never assume a field is empty. Always:
```
powershell -File adb-drive.ps1 type-field -Serial <id> -Text "the text"
```
This clears first (keyevent 123 to end-of-field, then keyevent 67 x30) before typing, so stale
content (`rev-4828-g1rev-4828-g1`) can't concatenate onto what you send. `clear-field` alone is
available if you need to blank a field without typing anything after.

## Dismissing the keyboard

```
powershell -File adb-drive.ps1 dismiss-keyboard -Serial <id>
```
This sends keyevent 4 (back). **Never send keyevent 111** - on this device family it opens Gboard
settings and derails the flow instead of dismissing the keyboard.

## Installing a build

```
powershell -File adb-drive.ps1 install -Serial <id> -Apk <path-to.apk>
```

## Gotchas this skill exists to prevent

- **`-s <serial>` omitted.** A physical phone plugged in alongside the emulator makes bare `adb`
  fail, or worse, target the wrong device. `Resolve-Serial` in the script refuses to run any
  action with more than one device attached and no `-Serial` given.
- **Coordinate scale mismatch.** A screenshot's raw pixel size (what you read) and the coordinate
  space `input tap` expects (`wm size`, override if set else physical) can differ - e.g. captured
  at 1080x2400, tapped in a 900x2000 space. `tap`/`tap-and-capture` always convert using the actual
  `wm size` of the target device, never a hardcoded ratio.
- **Stale field contents.** Typing without clearing first concatenates onto old input.
  `type-field` always clears first.
- **keyevent 111 for keyboard dismiss.** Opens Gboard settings. Use keyevent 4 (`dismiss-keyboard`).
- **Tapping before the screen finished rendering.** Always screenshot, read, then decide - never
  fire a tap off a screenshot from a previous step.
- **A plain PowerShell `>` redirect on `screencap` output.** Corrupts the PNG (text-mode CRLF
  translation over a binary stream). The script always does the two-step screencap-to-device-then-
  pull, never a redirect.
- **Release Flutter builds produce no logcat output.** They log via `log()` from `dart:developer`,
  which release mode does not surface to `adb logcat`. If the app under test is a release Flutter
  build, the backend/API log is the diagnostic surface for a failed step, not the device log.

## Screenshot output location

Default output (when `-Out` is omitted) goes to `.for_bepy/screenshots/<session-id>/`, matching
`/close`'s per-session purge scheme - derived via `close/rename-session.ps1 -GetId`, never a
hand-rolled process-tree walk. Never point `-Out` at the folder root.

## Not in scope

Scripted Patrol test suites (separate tooling, not this skill) and Flutter web (`/flutter-e2e`,
Playwright-driven, a different surface entirely). This skill is interactive native-Android UI
driving via adb only.

## Verification status

`adb` exists on this machine and one physical device was attached during authoring. Verified live,
read-only, against that device: `devices`, `wait-boot` (already-booted device, returns
immediately), and the `wm size` parsing logic (both a no-override and a synthetic override case).
**Not verified**: `screenshot`, `tap`/`tap-and-capture`, `clear-field`/`type-field`,
`dismiss-keyboard`, and `install` were not run - they would tap, type into, screenshot, or install
onto Joe's live personal phone, which is out of scope for authoring this skill. No emulator was
booted in this session either. Treat those code paths as reviewed-but-unverified until the first
real session exercises them, and report back anything that doesn't match.
