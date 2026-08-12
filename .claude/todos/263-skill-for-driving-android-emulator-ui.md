<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Skill for driving an Android emulator through a UI flow via adb

**Type:** skill-improvement
**Origin:** ai

## Goal

A skill that drives an installed Android app through a UI flow with `adb`:
tap, type, dismiss keyboard, screenshot, read back, repeat. The tap/screenshot/
inspect loop was hand-rolled roughly 20 times in one session on 2026-08-12, and
the same avoidable mistakes recurred within that single session.

## Context

Session of 2026-08-12 on `revaire-mobile` drove an ephemeral build through the
backend gate, onboarding, phone login, OTP, Google sign-in and a registration
attempt - every step an ad-hoc `adb shell input tap X Y` plus `screencap` plus
`pull` plus `Read`. There is no skill for this; `/flutter-e2e` covers **Flutter
web via Playwright**, not a native Android emulator.

Mistakes made, all of which a skill would have prevented:

- **Stale field contents.** A text field retained earlier input and produced
  `rev-4828-g1rev-4828-g1`. A field must be cleared (keyevent 123, then ~30x
  keyevent 67) before typing.
- **keyevent 111** was used to dismiss the keyboard and opened Gboard settings
  instead, derailing the flow. The correct key is keyevent 4.
- **Coordinate scaling.** Screenshots come back scaled (1080x2400 shown at
  900x2000), so every tap needs the multiplier applied. Done by hand each time.
- **Tapping before verifying.** Several taps fired against a screen that had not
  finished rendering, wasting a round trip. Screenshot-then-tap is the reliable
  order.
- **Wrong device.** Joe's physical phone was attached alongside the emulator, so
  bare `adb` failed with "more than one device". Every call needs `-s <serial>`.

## Approach

New skill, e.g. `~/.claude/skills/android-drive/SKILL.md`. It should:

1. Resolve the target serial explicitly and refuse to run if more than one device
   is attached without one given.
2. Provide a `tap-and-capture` step: screenshot, read, tap, wait, screenshot -
   so the model always sees the result of its own action.
3. Handle the coordinate multiplier automatically from the screenshot's reported
   scale, rather than making the model compute it per tap.
4. Provide `clear-field` and `type-into-field` helpers that always clear first.
5. Pin the keyevent table (4 = back/dismiss keyboard, 67 = delete, 123 = move
   end) and explicitly forbid 111.
6. Write screenshots into the per-session `.for_bepy/screenshots/<id>/` folder so
   `/close` can purge them by ownership.
7. Note that release Flutter builds log via `log()` from `dart:developer` and so
   produce **no** logcat output - the backend log is the diagnostic surface, not
   the device.

Check first whether this belongs inside the existing `/flutter-e2e` skill as a
second mode rather than a new skill; that skill already owns "drive the app
through a flow", just on a different surface.

## Acceptance

- A session can drive an Android app through a multi-screen flow without
  hand-writing `adb shell input` calls.
- The five failure modes listed above are structurally prevented, not just
  documented as warnings.
- Verified by re-running the ephemeral login flow from
  `revaire-mobile/.claude/todos/027-apple-login-and-build-discovery.md`.
