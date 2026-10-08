---
name: android-drive
description: "Drives an installed Android app via adb: tap, type, screenshot. Not Flutter web (/flutter-e2e) or Patrol."
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

## Proving an animation runs

A still screenshot can't show motion. Use `record-motion`, never a hand-rolled loop of separate
`adb shell` calls with `Start-Sleep` in between - see Gotchas for why that fails:
```
powershell -File adb-drive.ps1 record-motion -Serial <id> -Steps "wait:1500;tap:76,153;wait:2500;key:4;wait:2000;tap:957,2088" -Out <path.mp4> [-Strips "1.5,5.0"] [-TimeLimit 16]
```
- `-Steps` is a `;`-separated list of `tap:X,Y` / `wait:MS` / `key:CODE` tokens, built into ONE
  device-side shell string (`screenrecord ... & input tap ...; sleep ...; wait`) so timing is
  accurate by construction. `tap:X,Y` coordinates are PNG-space, read off a screenshot the same
  way `tap`/`tap-and-capture` expect - the script takes its own reference screenshot first and
  applies the identical PNG-size-vs-`wm size` scaling, so raw unscaled coordinates never reach
  `input tap`. Put any lead-in delay (recording needs a beat to start) as the first `wait` token.
- Pulls the mp4 to `-Out` (default screenshot dir, `.mp4`) and deletes the device-side temp file.
- Always emits a whole-video contact sheet (`fps=2,tile=8x4`) alongside the mp4 - this is what
  actually shows a botched drive at a glance instead of guessing at offsets.
- `-Strips "t1,t2,..."` additionally emits one short frame strip per timestamp
  (`fps=25,scale=200:-1,tile=10x1`, 0.4s window). Two strips at different timestamps must differ
  in file size - identical sizes mean the recording didn't move between them.
- If `ffmpeg` isn't found (PATH, then the known scoop shim), the mp4 still pulls; the output says
  `contactSheet=skipped(ffmpeg-not-found)` instead of throwing.

## Gotchas this skill exists to prevent

- **`-s <serial>` omitted.** A physical phone plugged in alongside the emulator makes bare `adb`
  fail, or worse, target the wrong device. `Resolve-Serial` in the script refuses to run any
  action with more than one device attached and no `-Serial` given.
- **Coordinate scale mismatch.** A screenshot's raw pixel size (what you read) and the coordinate
  space `input tap` expects (`wm size`, override if set else physical) can differ - e.g. captured
  at 1080x2400, tapped in a 900x2000 space. `tap`/`tap-and-capture` always convert using the actual
  `wm size` of the target device, never a hardcoded ratio.
- **Landscape rotation: `wm size` stays stale, screenshot doesn't.** On a rotated device `wm size`
  can keep reporting the pre-rotation (portrait) resolution while `screencap` already captures the
  rotated frame, e.g. `pngSize=2400x1080 wmSize=1080x2400`. Scaling off that mismatch crosses the
  axes (`scaleX=2.222 scaleY=0.45`) and every tap lands somewhere unrelated. The script detects an
  exact WxH swap between PNG and `wm size` and applies no scaling in that case, since `input tap`
  is already operating in the screenshot's own space. `screenshot`'s output now includes
  `orientation=`/`rotated=` so a wrong conversion is visible before a tap fires.
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
- **Host-side sleeps drift during a recording.** Timing a tap sequence with separate `adb shell`
  calls and PowerShell `Start-Sleep` in between looks fine until `screenrecord` is running - each
  round trip costs enough under that load that a sequence timed for 1.5s/3.2s/5.2s lands several
  seconds late, the recording ends before the interesting transition, and a tap can miss entirely.
  `record-motion` puts every `sleep`/`input tap`/`input keyevent` into the SAME device-side shell
  string as `screenrecord`, so there is no host round trip to drift.
- **`ffmpeg -ss` before `-i` silently lies.** Placed before the input it snaps to the nearest
  keyframe, so two different requested timestamps can return byte-identical strips (this is how
  the bug was caught - two "different" strips at 79179 bytes each). `record-motion` always puts
  `-ss` after `-i` for both strips and the contact sheet, so no caller can get the order wrong.
- **Raw `input tap` in a recording sequence needs the same scaling `tap` already applies.** The
  coordinates you read off a screenshot are PNG-space; `input tap` expects `wm size` space. A FAB
  tapped at the PNG's y=1852 instead of the scaled y=2088 simply does nothing, with no error.
  `record-motion` takes its own reference screenshot and applies the identical conversion before
  building the device-side shell string, so `-Steps` coordinates stay PNG-space like everywhere
  else in this skill.

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

2026-08-13 in `ssy-mobile`: a real session exercised `screenshot`, `tap`/`tap-and-capture`,
`type-field`, `dismiss-keyboard`, and `install` on `emulator-5554` and found the landscape
coordinate bug (todo 349) - `wm size` staying at the pre-rotation resolution while `screencap`
already reflects the rotated frame, crossing the scale axes. The workaround (raw `input tap` at
screenshot-pixel coordinates, no scaling) was confirmed correct across a ~20-step flow. The script
now detects that exact case (PNG/`wm size` differ only by a WxH swap) and applies no scaling,
matching the confirmed workaround; this was checked offline (dimension-pair unit checks against
both the portrait and the recorded landscape case) but **not yet re-run against a live rotated
device through the script itself** - report back if the first such run doesn't match.
**Still not verified**: `clear-field` in isolation (only `type-field`, which calls the same clear
path, has run).
