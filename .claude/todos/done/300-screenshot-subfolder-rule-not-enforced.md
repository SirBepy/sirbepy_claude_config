<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Verification screenshots keep landing outside the per-session subfolder

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the "throwaway screenshots go in `.for_bepy/screenshots/<pid>-<start-ticks>/`" rule actually
hold, instead of depending on the writing session remembering it.

## Context

Global `CLAUDE.md`, UI & visual changes section, requires throwaway verification screenshots to go
in a per-session subfolder so `/close` can prove ownership and delete only its own. `/close`
Phase 3 step 3 is built entirely around that: it refuses to delete by mtime, and will only touch
`.for_bepy/screenshots/<id>/`.

Violated on 2026-08-12 in `zng-app`. The session screenshotted a review deck straight into
`.for_bepy/screenshots/deck/`, a hand-named folder. The session id was `37260-134310201954151207`,
so `/close`'s purge would have found nothing and left the files behind forever. It only got cleaned
because the closing session happened to remember it had created `deck/`.

The root cause is that nothing enforces it. The rule lives in prose in `CLAUDE.md`, the path is
constructed by hand in whatever ad-hoc script the session writes, and the id itself needs
`rename-session.ps1 -GetId` to resolve, which is easy to skip when you are mid-task and just want a
PNG on disk.

Evidence of it being a recurring shape rather than one slip: `.for_bepy/screenshots/` in `zng-app`
currently holds ~40 loose root-level files plus 8 correctly-named subfolders, and `/close` treats
the loose ones as untouchable legacy, so they accumulate permanently.

## Approach

Pick one, in rough order of preference:

1. A tiny shared helper that returns the correct directory, creating it if needed, so no caller
   ever builds the path by hand. It would wrap `rename-session.ps1 -GetId`. Every skill that
   screenshots (`/screenshot`, `/verify`, `/flutter-e2e`, `/android-drive`, ad-hoc Playwright)
   calls it instead of hardcoding.
2. A `PostToolUse` hook that watches for image writes under `.for_bepy/screenshots/` at the root or
   in a non-conforming subfolder and either moves them or warns loudly.
3. At minimum, have `/close` report loose root-level files as a named finding rather than a silent
   count, so the pile stops being invisible.

Decide whether legacy root files should be swept once, or left alone permanently.

## Acceptance

- A session that writes a screenshot without thinking about the rule still ends up in the right
  folder, or is told immediately that it did not.
- `/close`'s purge count stops depending on the writing session's memory.

## Notes

Do not do this work from inside a project session. It belongs to a session working on
`C:\Users\tecno\.claude` itself.
- Done 2026-08-13, as a helper rather than more prose. New session-shot-dir.cjs computes and creates the per-session dir; screenshot-helper.cjs's resolveScreenshotPath() auto-resolves a bare filename into it and THROWS before launching a browser if a path targets the screenshots root directly. flutter-e2e's SHOT_DIR placeholder, which previously had to be hand-filled, now resolves automatically. Verified live both ways: the root-write attempt was refused with an actionable message, and bare-filename mode saved into the correct subfolder. android-drive was left alone: its adb-drive.ps1 already self-enforced in code.

- Renumbered 287 -> 300 on 2026-08-13 (todo 286): id 287 was claimed by two different files. The other file kept it because it was filed earlier. Any older reference to todo 287 may mean this one.
