<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 359 (done) is "project config does not state the timezone" (a config-content gap); SKILL.md already states the timezone and the conversion DIRECTION correctly. This is about a value getting mislabeled mid-reasoning AFTER a correct conversion, a different failure class with no existing todo. -->
# clockify-reconciliator: add a safeguard against relabeling a converted timestamp mid-reasoning

**Type:** skill-improvement
**Origin:** ai

## Goal

A future `/clockify-reconciliator` run can't silently carry a UTC-converted value forward as if it
were still local time, the way this session did.

## Context

2026-10-16/17, zng-app session, Zirtue reconciliation. `git log --pretty=format:"%aI"` already
prints the author's local time WITH its offset applied (e.g. `2026-10-16T14:32:39+02:00` means
14:32:39 IS the real Zagreb wall-clock time - confirmed by comparing it against `%ad
--date=format:"%H:%M:%S"`, which uses the system's own local timezone and matched exactly).

Claude correctly converted that value to UTC once, for an internal cross-check against a Clockify
API timestamp (`14:32:39 local - 2h = 12:32:39 UTC`), but then kept carrying the bare number
`12:32:39` forward through the rest of the session's reasoning - a dual-bound subagent dispatch, a
question posed to the dev, and the actual Clockify time-entry write - mislabeled as "local" the
whole way. The result: a logged time entry sat 2 hours before the commit it was supposed to cover.

SKILL.md step 3 already states the conversion rule correctly ("Convert explicitly in BOTH
directions... Europe/Zagreb local to UTC when writing... UTC to Europe/Zagreb when reading") - the
gap isn't a missing rule, it's that nothing in the skill guards against a value that's ALREADY been
converted getting silently relabeled and reused later in the same multi-step reasoning chain. The
bug wasn't caught by the skill's own process; it was caught because the dev pushed back ("are you
sure you can't find 20 hours this week?"), which triggered a closer re-check. A 3-agent
verification panel afterward confirmed the fix held, but that panel was dev-requested after the
dev noticed something felt off, not a standing part of the skill's own flow.

Full writeup and the fix that's already in place for future runs of this exact session's week:
`Clockify.md` in the Obsidian vault, "A commit's `%aI` timestamp is ALREADY local, don't
re-subtract an offset from it" section (added 2026-10-16/17, same incident).

## Approach

Add an explicit safeguard to `SKILL.md` step 3 (or wherever timestamps get compared/converted
across steps 6/6a/7/7a), one or both of:

1. **Tagging convention**: any time Claude's own working notes/reasoning carries a timestamp across
   more than one step, write it with an explicit `LOCAL=`/`UTC=` prefix, never a bare clock value
   (e.g. `LOCAL=14:32:39` not just `14:32:39`). Cheap, no tooling change, just a documented
   discipline the skill asks for explicitly rather than leaving to default judgment.
2. **Re-derive, don't reuse**: when a timestamp is needed again later in the same run (a subagent
   dispatch, a user-facing question, the actual API write), re-derive it from the ORIGINAL source
   (`%aI` for a commit, the API's raw `Z`-suffixed field for Clockify/Shortcut/HubStaff) instead of
   reusing an already-converted intermediate value carried in context. More robust than tagging
   alone, costs an extra fetch/recompute.
3. **Spot-check line in step 6**: when first reading commits for a run, print one commit's `%ad`
   (system-local) next to its `%aI` (author-local-with-offset) side by side, confirm they match (as
   this session eventually did only after the bug was already found), and state the confirmed
   local-time convention once at the top of the run's own output - gives the dev a cheap way to
   catch a mismatch early if the two ever diverge (different machine timezone, a commit authored
   from a different timezone than the dev's own).

## Acceptance

- SKILL.md states the relabeling risk explicitly, not just the correct conversion direction.
- A future run has a concrete mechanism (tagging, re-derivation, or the spot-check line) that would
  have caught this exact bug class before a Clockify write, not after a dev's pushback.

## Notes

This is a reasoning-discipline gap, not a logic bug in the skill's documented rules - the existing
step 3 text is accurate, it's just insufficient to prevent a value from getting silently relabeled
three steps downstream of where it was converted.
- Completed 2026-10-23 (loop-todos cycle 1) in the clockify-reconciliator batch commit.
