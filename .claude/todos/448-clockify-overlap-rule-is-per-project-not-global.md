<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=8, reconfirm-count=2, content-hash=52ba2907 -->
<!-- duplicate-checked -->
# Clockify overlap ban is global but should be per-project, and the override keeps getting re-asked

**Type:** skill-improvement
**Origin:** dev

## Goal

`~/.claude/skills/clockify-reconciliator/SKILL.md` states one flat no-overlap rule. The dev's actual
rule is narrower: overlap within the SAME Clockify project is banned, overlap ACROSS projects is
fine. Encode that, so a multi-project week stops needing a live override every single run.

## Context

Asked for directly by the dev on 2026-08-20, in his words: "dont overlap entries from the same
project, but overlap with other projects is fine, ideally not during meeting times, but its still
alowed, leave a /create-todo to update this skill, cuz we keep not following those rules frequently."

Trigger: a two-project reconciliation (Revaire + Zirtue, Mon-Wed 2026-08-17..19, 18h target each).
Those two projects are billed separately and the dev genuinely works them in the same wall-clock
hours, so a global no-overlap rule makes the second project's 18h unreachable by construction.

The current rules that collide with this, all in `SKILL.md`:

- `SKILL.md:210-212` - "must not overlap another same-day entry - shift/shrink the new block instead
  of double-counting". Written as if all entries share one timeline. It does not scope by project.
- `SKILL.md:110-111` (step 4a) - same instruction again, sourced from the `feedback_clockify_*.md`
  memories. Two statements of one rule, so a fix must touch both or they drift.
- `SKILL.md:201-212` - the "never touch existing / never add net-new hours" defaults, escapable only
  via Audit mode (step 3a).

Distinct from [[34-clockify-reconciliator-audit-mode]] (done, commit `8d83c75`), which CREATED Audit
mode. This todo is about the mode boundary being wrong, not missing: the dev keeps having to grant
the Audit override for what is, for him, routine multi-project reconciliation.

## Approach

1. Scope the overlap rule by `clockify_project_id`. Same project, overlap is a hard error, unchanged.
   Different project, overlap is allowed and needs no override. Fix both statements (`SKILL.md:210`
   and the step 4a restatement at `:110`) in the same edit so they cannot drift apart.
2. Add a soft meeting-time preference: prefer not to place a new block over a known meeting window,
   but allow it. Explicitly NOT a hard constraint - the dev said "ideally not, but its still alowed".
   No meeting source is configured today; the recurring-standup idea in `34`'s Approach is the
   closest prior art. Do not invent a calendar integration for this - if no meeting source exists,
   the preference is a no-op and should say so rather than silently doing nothing.
3. Re-check whether cross-project reconciliation still deserves the full Audit gate once overlap is
   per-project. Adding to a day that already has entries is the remaining trigger. Consider a
   narrower, named override so the common case stops re-prompting.
4. Check the `feedback_clockify_*.md` memories that step 4a defers to. If one of them states the flat
   no-overlap rule, it must be updated too, or the skill will keep re-importing the old rule.

## Acceptance

- A run reconciling two Clockify projects over the same hours writes overlapping cross-project
  entries without asking for an override.
- Two entries in the SAME project still never overlap; that check stays hard and stays enforced.
- No statement of the overlap rule survives anywhere that omits the project scoping - grep
  `SKILL.md` plus the clockify memory files and confirm every hit carries it.
- The prior behavior does not regress: descriptions with content stay untouched outside Audit mode,
  and unbacked hours are still never invented (`SKILL.md:204-206`).

## Notes

- The dev's framing was that the rules "keep not being followed". Read that as the defaults being
  wrong for his actual workflow, not as an enforcement problem - tightening the wording alone has
  already failed once for a rule in this family (root `CLAUDE.md` notes the same failure mode for
  the em-dash rule).
- Open, not decided: whether a meeting-time source is worth configuring at all, or whether step 2
  should stay a documented preference with no data behind it.
- Related incident (2026-08-21/22, zirtue project, revaire session logging into the same workspace
  concurrently): the same missing project-id scoping caused a WORSE bug than the overlap question
  this todo was filed for. An ad-hoc Clockify fetch built later in the run (to sum a weekly total,
  and again to build a HubStaff-mirroring entry list) queried the whole workspace without filtering
  by `projectId`, silently pulling in ~20 unrelated revaire entries and inflating a reported "30h"
  total by about 1h45m of someone else's project's time before it was caught (by a dev-requested
  3-subagent verification pass, not caught proactively). Only step 4's ORIGINAL fetch bucket was
  ever project-scoped; every later ad-hoc fetch in the same run re-derived its own query and forgot
  the filter. When fixing this todo's overlap scoping, also audit every OTHER place in the skill
  (and any inline follow-up query a session writes mid-run) that sums/lists Clockify entries -
  `clockify_project_id` filtering needs to be a hard, impossible-to-skip step of the fetch helper
  itself, not a convention each call site has to remember.
