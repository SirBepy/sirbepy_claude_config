<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# clockify-reconciliator project config does not state the dev's timezone

**Type:** skill-improvement
**Origin:** ai

## Goal

Record the local timezone in the clockify-reconciliator's per-project config so a
run does not have to infer it, and cannot infer it wrongly.

## Context

Surfaced 2026-08-16 by a reconciliator run on `revaire-mobile`. The Clockify API
stores entry times in UTC, and the run was asked to log a block described in
local time (15:56 to 18:05). Nothing in
`~/.claude/skills/clockify-reconciliator/projects/` states which timezone the
dev's local times are in.

That run got it right, but only by **deriving** the offset: it diffed the UTC
timestamps of already-existing entries against their known local times and
concluded UTC+2. That works only while prior entries for the same day already
exist. A day whose first entry is written by the reconciliator itself has
nothing to diff against, so the same inference is unavailable exactly when it is
needed most.

The failure mode is silent and expensive to spot: entries land in the right
duration but the wrong hour, which looks completely normal in a weekly total and
only shows up if someone compares an entry against when the work actually
happened.

Croatia is UTC+1 in winter and UTC+2 in summer, so a hardcoded offset is wrong
half the year. Whatever is recorded must be the zone name, not a fixed offset.

## Approach

1. Add the IANA zone (`Europe/Zagreb`) to the per-project config under
   `~/.claude/skills/clockify-reconciliator/projects/`. Check whether that
   belongs per-project or once at the skill level - the dev is in one place, so
   skill level is probably right and per-project is redundant.
2. Have `SKILL.md` instruct the run to read it and convert explicitly, rather
   than deriving the offset from existing entries.
3. Keep the derive-from-existing-entries trick as a documented FALLBACK, since
   it did work here. Note its limitation: unavailable on a day with no prior
   entries.

## Acceptance

- A reconciliator run on a day with zero pre-existing entries writes them at the
  correct local hour.
- The config states a zone name, not a fixed numeric offset, so DST is handled.
- No existing entry is rewritten as part of this change.

## Verify

- [ ] `ls ~/.claude/skills/clockify-reconciliator/projects/`
- [ ] grep the skill for existing timezone handling before adding a second one

## Notes

- Filed from a `revaire-mobile` session per the rule that findings about the
  `~/.claude` tree belong in this backlog. Not fixed there: editing global
  tooling from a project session needs the dev's say-so in that session.
- The 2026-08-16 run itself is fine. Its entries were verified against real
  commit timestamps and landed correctly. This is about the next run, on a
  quieter day.
- Done 2026-08-17: recorded Europe/Zagreb at SKILL LEVEL, in step 3 (Resolve window), not per project - the dev is in one place, so a copy in each projects/*.md would only be a second thing to keep in sync. The zone NAME is recorded, never a numeric offset, so DST is handled. Step 3 now also states that Clockify stores UTC and requires explicit conversion in both directions, and keeps the derive-from-existing-entries trick as a documented FALLBACK with its limitation named (unavailable on a day whose first entry is the one being written). Verified the skill had no prior timezone handling to collide with: it said 'dev timezone' in four places and never once said which, and never mentioned UTC at all. No existing Clockify entry was touched.
