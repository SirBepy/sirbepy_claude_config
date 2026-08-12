<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=8, reconfirm-count=2, content-hash=bd67fc83 -->
# Extend clockify-reconciliator with a full-month audit/reconstruction mode

**Type:** skill-improvement
**Origin:** ai

## Goal

`~/.claude-personal/skills/clockify-reconciliator/SKILL.md` currently only documents "fill empty
descriptions on existing entries." A 2026-07-30 session on the fibo project used it as the seed
for a much bigger job the skill doesn't describe at all: reconstructing entire missing days from
git history, and auditing/fixing an already-populated month for padding, overlaps, and validity
before a client report went out. It worked, but every rule of engagement was improvised live in
chat instead of being encoded in the skill, so the next cold session starting from the same ask
has to re-derive all of it from scratch.

## Context

Session shape (fibo/frontend2, `/clockify-reconciliator`):
1. Dev said "I haven't clocked any hours this week" - zero existing entries, so the skill's core
   rule ("never create entries in empty time ranges, only operate on existing entries") had to be
   explicitly overridden with the dev's permission. A full week was built from commit clusters,
   the recurring daily standup (09:45-10:00 local), and bike-rental-app timestamps used to bound
   in-person meetings (first ride before 1PM = commute in, second ride or a post-1PM ride = commute
   out; no return ride = "didn't bike home", a real recurring case).
2. Dev then asked to fix "the whole month," which meant editing entries that already had
   non-empty descriptions - the skill's other core rule, also explicitly overridden.
3. Real bugs were found this way that a single pass missed: two separate cases of overlapping
   entries (two entries both claiming the same clock window - a hard logic error, not a judgment
   call), several "mechanical equal-split" artifacts (2-3 consecutive entries with near-identical
   durations down to the second, a sign a big raw block got auto-split without checking for real
   gaps), and entries whose own described commit actually happened in a *different* entry's time
   window.
4. Verification only converged after 4 independent agent passes: two `sonnet` agents hunting for
   padding from different date ranges, one `opus` agent specifically tasked with arguing the
   opposite direction ("did we trim too aggressively, should something be LONGER"), and one final
   solo `opus` read-only holistic pass explicitly told not to just re-confirm prior findings. Each
   pass found something the others missed (see Approach for the exact prompts).
5. Even after all 4 passes, the DEV caught something no agent flagged: two short (15-20min)
   entries separated by a 2-hour gap late at night, which he correctly identified as one
   continuous session (design iteration between two commit clusters) that had been artificially
   chopped into two islands by the reconstruction process. This "chopped session" shape - two
   short entries flanking a multi-hour gap with nothing else nearby - is a distinct failure mode
   from ordinary padding and none of the 4 agent passes were told to look for it specifically.

## Approach

Add a second documented mode to the skill (or a sibling skill/section), roughly:

- **Reconstruction mode**: triggers when the date range has zero or sparse entries. Sources, in
  priority order: git commits (author-date, all branches, deduped across rebase/cherry-pick
  duplicates by matching message+near-timestamp), the recurring standup block if one is
  established in the project config, and an optional "commute app" timestamp source (generalize
  the bike-rental-app pattern - first daily entry before ~1PM = arrival, a second same-day entry
  or one after ~1PM = departure, missing departure is normal and not an error) for bounding
  unexplained gaps as likely in-person meetings. Always ask the dev to confirm meeting content/
  duration from memory rather than inventing it - durations anchored to commute timestamps are a
  starting hypothesis, not ground truth, and the dev's own memory should win when it conflicts
  (this session had the dev explicitly override an agent's padding-driven trim of a real
  meeting once he confirmed the longer duration from memory).
- **Audit mode**: triggers on an explicit "check/fix the whole month" type ask. Requires the dev's
  explicit override of the two "don't touch existing/don't create in gaps" rules, scoped to
  "session" not "forever." Checklist to run, cheapest first:
  - Hard overlap check: any two entries in the range with overlapping `[start,end)` - always a
    bug, fix immediately, no judgment call.
  - Mechanical-split fingerprint: consecutive entries with near-identical (within a few seconds)
    durations - re-derive each half's real commit backing independently rather than trusting the
    original split point.
  - Chopped-session fingerprint: two short entries (roughly <30min) separated by a gap of an hour
    or more with nothing else in between, on the same night/day - default hypothesis is ONE
    continuous session with untracked (non-commit) work in the gap; ask the dev before assuming
    it's two real separate sessions instead.
  - Total-duration sanity: any single day over ~9-10h, or a duration wildly disproportionate to a
    trivial-sounding description, gets a second look.
- **Multi-pass verification** as a documented, reusable pattern (not something to re-derive per
  session): 2 independent agents padding-hunting from different angles/date ranges, then 1 agent
  explicitly tasked as devil's-advocate-for-longer (catches over-correction), then 1 final
  high-reasoning **read-only** solo pass explicitly told to look for systemic/holistic issues
  (overlaps, internal inconsistency across days, "does this look reverse-engineered") rather than
  re-litigate individual entries. Every subagent must be told explicitly whether it has write
  access or is report-only, and given the live API key/workspace/project ids inline in the prompt
  since these subagents need to independently re-pull data, not trust a prior agent's summary.
  All dispatches still follow the global sonnet-by-default / opus-only-for-final-solo-verify rule.

- **Gap detection as a mandatory step in EVERY mode, including plain reconciliation** (added
  2026-08-03 after the failure below). Between the current step 6 (read commits) and step 7 (build
  proposals), pull the dev's commits for the WHOLE window - not just for already-identified targets
  - and diff them against the entries that exist. Any day or multi-hour block with commits and no
  covering entry is a finding and goes in the step 9 proposal table next to the empty-description
  targets. The existing rule "never create entries in empty time ranges" must be reworded so it
  reads as "never invent time", not "never look at unlogged days": the ban is on unbacked hours,
  not on surfacing commit-backed gaps for the dev to approve.

## Acceptance

- A cold session given "reconcile my whole month, I think some of it might be off" can follow a
  documented procedure instead of improvising the override permissions, the reconstruction
  sourcing, and the verification fan-out from scratch.
- The chopped-session check and the hard-overlap check are explicit, named checklist items - not
  something that only surfaces if the dev happens to eyeball the result and catches it themselves.
- A window containing a fully unlogged workday can NEVER be reported as "nothing to reconcile".
  Regression case: 2026-08-03, `/clockify-reconciliator` run for "Thursday till now" reported done
  after filling one description, while Fri 2026-07-31 held ~25 of the dev's commits and zero
  entries (~8h). The run even printed "no entries at all that day" and still only proposed adding a
  15-minute standup. The dev caught it: "you sure i did NO work on friday?"
- Every entry the skill creates or edits has start AND end on a 5-minute boundary (:00/:05/:10...).
  Stated by the dev 2026-08-03; commit-derived boundaries plus 20min padding land on arbitrary
  minutes and imply a precision the evidence doesn't support. Round the shared boundary of
  contiguous chunks once, so rounding introduces neither a gap nor an overlap.

## Notes

Folded in from todo 138 (archived 2026-07-31, superseded by this one) - the proven clustering
defaults from the 2026-07-21 TabsxLabs bootstrap (46 entries created): session break at a 3h
commit gap; pad each session +20min lead-in and +20min trail-off; split sessions over 3h into
~2-2.25h sub-chunks with per-chunk commit-derived descriptions; carve named recurring non-commit
activities (e.g. daily 09:45-10:00 standup) around sessions instead of double-booking; create via
POST (reconciliation mode stays PUT/description-only). Hard rule to encode, enforced twice that
session: never invent hours not backed by a real commit/PR or an explicitly named real activity -
a weekly cap is a ceiling, never a target. Ids/keys in `project_fibo_personal_clockify.md`.

Nothing was actually broken by this gap - the dev's fibo Clockify data for July 2026 was fixed
correctly by the end of the session, this todo is purely about not re-paying the "improvise the
whole methodology in chat" cost next time the same kind of ask comes in, possibly on a different
project (the reconstruction/audit logic here isn't fibo-specific).

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 178; renumbered to 34 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: add Reconstruction mode, Audit mode and a mandatory gap-detection step to
  `clockify-reconciliator/SKILL.md` per the fully specified Approach - commit-cluster sourcing, a
  3-hour session-break gap, a 20-minute pad, the overlap and mechanical-split and chopped-session
  checklist, the 4-pass verification pattern, and 5-minute boundary rounding. This was produced by a
  strict second-pass re-triage that specifically asked whether a defensible answer exists without
  the dev; it concluded yes. Not executed only because the session ended.

- **Re-confirmed 2026-08-10 (zng-app):** the weekly-target-fill exception (real commits, zero-entry
  days only, never touching a day that already has entries) worked cleanly end to end - 5h20m
  gap-filled across Fri/Sat from real git evidence to hit a 30h weekly target, landing on exactly
  30:00:00, dev-approved via AskUserQuestion before writing. Confirms the "weekly cap is a ceiling,
  never a target you invent hours to hit" framing still needs one caveat encoded: filling TOWARD an
  explicitly dev-stated target, sized from real evidence, is allowed - it's inventing UNBACKED hours
  that's banned. Separately surfaced a new gap this session (HubStaff sync scope defaults) - see
  [[73-hubstaff-sync-scope-default-full-not-touched-slice]], not folded into this todo since it's
  about `hubstaff.md`, not `SKILL.md`.
