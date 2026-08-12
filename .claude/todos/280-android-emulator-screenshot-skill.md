<!-- Claim before executing: ~/.claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=6, reconfirm-count=2, content-hash=ef742b7e -->
# Skill candidate: drive + screenshot an Android emulator

**Type:** skill-improvement
**Origin:** ai

## Goal
Stop re-deriving the adb screenshot and boot-wait loop in every mobile session.

## Context
On 2026-08-11 in `revaire-mobile` the same three sequences were hand-written
repeatedly:

- **screencap + pull + read**, six times:
  `adb -s <dev> shell screencap -p /sdcard/x.png` then `adb pull` to
  `.for_bepy/screenshots/<session>/`, then Read. Note a plain PowerShell `>`
  redirect corrupts the PNG, which is why the two-step form is required.
- **boot the AVD and wait**, three times: `Start-Process emulator.exe -avd ...`
  then poll `adb shell getprop sys.boot_completed` until it returns 1.
- **tap/type coordinates**, which are device pixels and need the screenshot's
  display scale applied (1080x2400 captured, shown at 900x2000, so x1.2).

Existing memories cover the individual gotchas
(`project_emulator_interactive_run`, `project_patrol_claude_runnable`) but there
is no skill, so each session rebuilds the loop from prose.

Also worth folding in: `-s <device>` must be passed explicitly whenever a
physical phone is also plugged in, or commands hit the wrong target. That nearly
installed a test APK onto Joe's Redmi.

## Approach
Author a small skill that wraps: ensure-emulator-running, wait-for-boot,
install-apk, screenshot-to-session-folder, and tap/type with scale conversion.
Build it with `/bepy-skill-creator` rather than hand-rolling. Keep it Android-adb
only - Patrol already covers scripted test runs, this is for interactive driving.

## Acceptance
A mobile session can boot an emulator, install a build, drive a flow and capture
screenshots without hand-writing adb incantations, and screenshots land in the
per-session subfolder `/close` expects.

## Notes

- Migrated on 2026-08-12 from the dead top-level `~/.claude/todos/` path (was #04 there). That location was superseded by the repo-relative backlog on 2026-08-11; nothing reads it, so these were invisible to the Conductor app.
