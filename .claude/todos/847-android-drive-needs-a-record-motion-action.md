<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# android-drive needs a record-motion action

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `android-drive` a first-class way to prove an animation runs, so the record-and-extract loop
stops being re-derived by hand with the same two mistakes each time.

## Context

pomalo session 2026-08-31. Joe reported an app had no animations; proving otherwise required
capturing motion, which a still screenshot cannot do. `adb-drive.ps1` has `screenshot`, `tap`,
`tap-and-capture`, `type-field`, `install` and `devices` - nothing for video. The loop was
hand-rolled **four times** before producing a usable artifact, failing the same two ways:

1. **Host-side sleeps drift.** The first attempt spaced taps with PowerShell `Start-Sleep`
   between separate `adb` calls. Each `adb shell` round trip costs enough under `screenrecord`
   load that a sequence timed for 1.5s/3.2s/5.2s landed several seconds late; the recording ended
   before the interesting transitions and one tap never registered at all. The fix is to put the
   sleeps ON the device inside a single shell string:
   `adb shell "screenrecord --time-limit 16 ... & sleep 1.5; input tap X Y; sleep 2.5; ..."`.
2. **`ffmpeg -ss` before `-i` silently lies.** Placed before the input it snaps to the nearest
   keyframe, so two different timestamps returned byte-identical strips (79179 bytes both times,
   which is the only reason it was caught). `-ss` must come after `-i`.

A third, unrelated-looking trap that is really the same class: tap coordinates read off a
displayed screenshot need scaling to the PNG's own pixel space. The skill's `tap-and-capture`
already handles this, but the raw `input tap` calls used for the recording drive do not, and a FAB
was tapped at y=1852 instead of y=2088 and simply did nothing.

## Approach

Add one action to `~/.claude/skills/android-drive/adb-drive.ps1`, roughly:

```
record-motion -Serial <id> -Steps "tap:76,153;wait:2500;key:4;wait:2000;tap:957,2088" \
              -Out <path.mp4> [-Strips "1.5,5.0"] [-TimeLimit 16]
```

- Builds ONE device-side shell string from `-Steps` so timing is accurate by construction, with
  the same PNG-space-to-`wm size` scaling `tap` already applies.
- Runs `screenrecord`, pulls the mp4, deletes the device-side temp file.
- For each timestamp in `-Strips`, emits a frame strip via
  `ffmpeg -i <in> -ss <t> -t 0.4 -vf "fps=25,scale=200:-1,tile=10x1"` - `-ss` after `-i`, encoded
  in the script so no caller can get it wrong.
- Also emit a coarse whole-video contact sheet (`fps=2,tile=8x4`) by default. That is what
  actually diagnosed the botched first attempt, because it shows at a glance where the drive
  went wrong instead of leaving you guessing at offsets.
- Guard: if `ffmpeg` is missing, still pull the mp4 and say the strips were skipped.

Document all three traps in the skill's "Gotchas this skill exists to prevent" section, which is
where the existing scale-mismatch and keyevent-111 notes live.

## Acceptance

- One `record-motion` call produces an mp4, a contact sheet, and the requested strips.
- Two strips requested at different timestamps differ from each other (the regression case for
  the `-ss` bug - compare file sizes, identical sizes mean it regressed).
- A tap sequence timed to 100ms lands on the intended widgets, verified by the contact sheet
  showing the expected screens in order.

## Notes

- `ffmpeg` is already on PATH on this machine (`C:\Users\tecno\scoop\shims\ffmpeg.exe`).
- Worked example with real output lives in the pomalo memory `android-animation-scale-conflation`
  and in `pomalo/.claude/todos/18`.
- `screenrecord --time-limit` self-terminates, so it does not need the orphan handling a
  long-lived process would.
