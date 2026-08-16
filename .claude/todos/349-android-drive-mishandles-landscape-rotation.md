# android-drive: tap coordinates are wrong on a rotated (landscape) device

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `skills/android-drive/adb-drive.ps1` compute correct tap coordinates when the device is in landscape, instead of silently mis-placing every tap.

## Context

Found 2026-08-13 in `ssy-mobile`, smoke-testing a release APK on `emulator-5554` (API 36). The app under test forces landscape.

Once the app rotated, every `screenshot` call reported:

```
pngSize=2400x1080 wmSize=1080x2400 scaleX=2.222 scaleY=0.45
```

The screenshot is landscape (2400x1080) while `wm size` still reports the physical portrait resolution (1080x2400). The script derives its scale factors from that mismatch and produces `scaleX=2.222 / scaleY=0.45`, which is not a rotation transform at all, just the two axes' ratios crossed over. Any X/Y read off the screenshot and passed to `tap`/`tap-and-capture` lands somewhere unrelated.

The skill's own docs already call out "coordinate scale mismatch" as the #2 gotcha the script exists to prevent, and claim `tap` "always converts using the actual `wm size` of the target device". That conversion is only correct while the device orientation matches `wm size`'s orientation.

`SKILL.md` also flags `tap`/`tap-and-capture` as **reviewed-but-unverified** under "Verification status". This is the first real session to exercise them, and it found the bug, exactly as that section invited.

## Workaround used

Bypassed the script for taps and used raw `adb shell input tap <x> <y>` with coordinates taken **directly from the screenshot's own pixel space**, no scaling. That worked on every tap across a ~20-step flow, because `input tap` operates in the current display orientation, which is the same space the screencap is captured in.

Note `type-field`, `dismiss-keyboard`, `install` and `screenshot` were all fine; only the coordinate conversion is affected.

## Approach

1. Detect rotation rather than assuming it: `adb shell dumpsys input | Select-String SurfaceOrientation`, or compare the screenshot's aspect against `wm size`'s.
2. When the screenshot's orientation differs from `wm size`'s, the correct scale is screenshot-space to *rotated* display space, not to raw `wm size`. In practice when the two match in area and only differ by transposition, the right answer is **no scaling at all**.
3. Keep the existing portrait path unchanged, it is correct there.
4. Have `screenshot` print the detected orientation alongside `pngSize`/`wmSize`, so a wrong conversion is visible before a tap is fired rather than after.
5. Update `SKILL.md`: move `tap`/`tap-and-capture` out of "not verified", and add landscape to the Gotchas list.

## Acceptance

- A landscape app can be driven end to end through `tap-and-capture` with no manual coordinate correction.
- Portrait behaviour is unchanged.
- `screenshot` output states the orientation it detected.
