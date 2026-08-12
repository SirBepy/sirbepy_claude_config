<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=8, reconfirm-count=2, content-hash=564e941b -->
# clockify-reconciliator: check existing memory + handle "day has some entries but real work unlogged"

**Type:** skill-improvement

## Goal

Update `~/.claude-personal/skills/clockify-reconciliator/SKILL.md` so two things that only got caught mid-session (2026-07-28) are baked into the skill instead of relying on the orchestrator to remember them: (1) always check existing `feedback_clockify_*` memories before proposing anything, (2) handle the case where a day has some entries logged but the dev recalls doing more real work that isn't reflected in any entry or tracker.

## Context

During a `/clockify-reconciliator zirtue yesterday` run, three separate corrections happened that a memory check up front would have caught before they reached the dev:

1. Skill defaulted a new entry to `billable: true`. Existing memory `feedback_clockify_no_billable_flag_no_overlap.md` (a prior correction from the same day, but the general Cinnamon convention predates it) says Cinnamon never marks entries billable.
2. The new entry overlapped an existing "Daily Standup" entry by a full hour - same memory file, second half of the rule: check same-day entries for overlap before creating.
3. The skill's own written rule ("never create entries in empty time ranges, only operate on existing entries") collided with a THIRD, separate standing memory `feedback_clockify_no_extra_hours.md` ("never add net-new hours to a day that already has entries, only reshuffle"). This one wasn't violated in the end - Claude caught it before /close and got explicit dev sign-off to treat it as an exception - but it should not require a self-catch; the skill's own decision tree should surface this fork.

All three memory files now exist and are correct. The gap is that `SKILL.md` has no step telling the orchestrator to load `feedback_clockify_*` memories before Step 5 (Identify targets), so a cold session repeats the same three corrections from scratch.

## Approach

In `~/.claude-personal/skills/clockify-reconciliator/SKILL.md`:

- Add a step (before Step 5, "Identify targets") that greps/reads `feedback_clockify_*.md` memory files for the resolved project and applies them: billable defaults, overlap checks, net-new-hours policy.
- Extend Step 5/7 to cover a day that has SOME entries logged (not just "empty description" targets, and not just the existing "zero commits, ask the dev" branch): if the dev recalls unlogged real work on a day that already has entries, this is currently undefined territory. Decision tree should be: (a) is there a commit/tracker trail for the extra time? if yes, propose it and explicitly call out the day-total change before applying, matching the confirmed exception in `feedback_clockify_no_extra_hours.md`; if no trail exists (pure recollection, e.g. manual UI testing), say so plainly and ask the dev for a number rather than inventing one, per `feedback_state_evidence_level_precisely.md`.
- Cross-reference `feedback_clockify_infer_project_from_cwd.md` too while in there - Step 1 ("Load config") should infer project from cwd match against `repos:` lists before asking, instead of always asking.

## Acceptance

- Running the skill on a day with existing entries no longer defaults to `billable: true`.
- Skill checks for overlap with existing same-day entries before creating anything.
- Skill has an explicit branch for "day has entries but real work is unlogged", instead of silently falling through the "empty description" flow (which finds nothing) or the "zero commits" flow (which doesn't apply since commits exist).
- Skill's project-name resolution checks cwd against configured repos before asking (see todo scope overlap with `feedback_clockify_infer_project_from_cwd.md`).

## Notes

All three underlying memory files already exist and are correct as of 2026-07-28:
- `feedback_clockify_no_billable_flag_no_overlap.md`
- `feedback_clockify_no_extra_hours.md` (updated same day with the net-new-hours exception)
- `feedback_clockify_infer_project_from_cwd.md`

This todo is purely about teaching the skill file to consult them proactively so future sessions don't need a dev correction to surface the same three issues.

**Reconfirmed 2026-08-06, bigger this time:** a `/clockify-reconciliator zirtue this week so far` run hit the exact same SKILL.md-vs-memory collision, but for three whole days (Mon/Tue/Wed) with almost nothing logged at all, not just one day. Claude initially reported "nothing to reconcile" (technically true under the skill's literal "fill empty descriptions only" scope) and it took the dev asking "add the missing entries... theres lots of them missing" to surface that most of the week was untracked. Two more gaps found in the same session, both belong in this todo's Approach:
- **Gap-fill sizing:** Claude's first pass proposed hours only for the immediate minutes around each commit (isolated clusters), undershooting a day with 6h12m between first and last commit. Dev pushed back ("u sure it was only 4:30 total hours today?"). Fix: default gap-fill day sizing to the full first-to-last-commit window chunked into 1-3h blocks, not isolated cluster minutes. See `feedback_clockify_no_extra_hours.md`'s 2026-08-06 addendum.
- **Step 4 fetch integrity:** the very first Clockify GET for the target window returned entries from a totally unrelated prior week (stale/cached response, confirmed by an identical immediate re-fetch returning the correct set). Add a check after Step 4: verify every returned `timeInterval.start` falls inside the requested window, re-fetch once if not - a stale response is indistinguishable from "genuinely nothing to reconcile" otherwise. See `reference_clockify_stale_first_fetch.md`.
- completed, commit 8d83c75
