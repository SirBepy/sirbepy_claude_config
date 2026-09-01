<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=2, content-hash=e227f1cd -->
# Fix the Obsidian daily-note automation (screenpipe pipe), then use it more

**Type:** task
**Origin:** dev

## Goal

Restore the screenpipe-powered Obsidian daily notes (`C:\Users\tecno\Documents\ObsidianVault\YYYY-MM-DD.md`,
hourly app-usage tables + transcribed conversations) so they're current again, then look at using
them more, e.g. as a secondary evidence source for `clockify-reconciliator`'s Reconstruction mode.

## Context

Discovered 2026-08-21 while running clockify-reconciliator for zirtue: the last daily note is
`2026-07-20.md`, over a month stale. The pipe script lives at
`C:\Users\tecno\.screenpipe\obsidian-pipe-run.ts`. The raw capture DB
(`C:\Users\tecno\.screenpipe\db.sqlite`, ~18GB) IS still live and updating (confirmed same day),
so the capture layer works; it's specifically the Obsidian-note generation pipe that stopped.

Dev's own read: "im pretty sure screenpipe is almost always off" - so the fix may need to start
with why screenpipe (the capture app itself) isn't running consistently, before the Obsidian pipe
can produce anything current. Don't assume the pipe script is the only broken piece.

When asked whether clockify-reconciliator should query the raw sqlite DB directly (bypassing
Obsidian) as a stopgap, dev declined - screenpipe being off most of the time means the data
wouldn't be reliable either way. That idea was dropped, not deferred; don't resurrect it as part
of this fix unless the dev raises it again.

## Approach

1. Check why screenpipe isn't staying on - autostart config, crash logs
   (`C:\Users\tecno\.screenpipe\screenpipe-app.<date>.log`, `last-panic.log.prev` already shows a
   past panic), or the dev just isn't launching it.
2. Once screenpipe capture is reliably running, check `obsidian-pipe-run.ts` and whatever
   schedules it (cron/task scheduler/pipe_scheduler_state table) for why note generation stopped
   even before the capture gap - check `pipe_executions` and `pipe_scheduler_state` tables in
   `db.sqlite` for the last successful run and any recorded error.
3. Once daily notes are current again, revisit whether clockify-reconciliator's Reconstruction
   mode (`~/.claude/skills/clockify-reconciliator/modes.md`) should add Obsidian daily notes as an
   explicit secondary evidence source (source #2/#3 already lists a "commute-app timestamp source"
   pattern this could follow) - a separate, smaller follow-up once the notes themselves are
   trustworthy again.

## Acceptance

- `ls C:\Users\tecno\Documents\ObsidianVault\*.md` shows a note for yesterday and today after a
  normal work day.
- Confirm what caused the stall (capture-app not running vs. pipe-script failure vs. scheduler
  issue) so it doesn't silently recur.

## Provenance

Filed 2026-08-21 as todo 176 in zng-app's backlog by a clockify-reconciliator session, then
re-filed here 2026-08-22 on Joe's instruction: it is global tooling (screenpipe, the Obsidian
vault, the clockify-reconciliator skill) with no zng-app content, so it belongs in this repo's
backlog per the CLAUDE.md rule that a finding about the global tree goes in the ~/.claude repo.
Content is otherwise unchanged.
