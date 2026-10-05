<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/905 covers the original bug (guessing a weekly-remaining figure from
an incomplete single-day fetch, now gated off); this is the opposite case - the dev explicitly asks
for the figure anyway and the skill has no sanctioned way to answer honestly -->
# clockify-reconciliator: no sanctioned path when the dev explicitly wants week-remaining on a partial window

**Type:** skill-improvement
**Origin:** ai

## Goal

Document a safe pattern in `skills/clockify-reconciliator/SKILL.md` step 9a for when the dev
directly asks "how many hours left this week" on a run whose window fails the full-week gate
(`today`, `yesterday`, a partial range), instead of leaving each session to improvise it.

## Context

2026-09-24, zng-app, `/clockify-reconciliator zirtue` for "today and yesterday". The full-week
gate (added by `done/905-clockify-visual-claims-weekly-remaining-on-a-single-day-run.md`) correctly
suppressed the target bar for this 2-day window. But the dev then asked directly: "your graphic
isnt showing me how many hours left we got for this week."

Handled ad hoc: ran a SEPARATE, explicit fetch for the real Monday-to-now range (existing entries
only, no guessing), summed it, added the session's own proposed hours on top, and rendered a
"this week so far" section below the main grid, clearly labeled as not gated behind the usual
check and sourced from a real fetch. This is safe (never assumes zero on unfetched days, the exact
failure mode 905 fixed) but was improvised - the skill gives no guidance on this specific,
apparently recurring ask.

## Approach

In step 9a, after the full-week gate's fallback (plain window total, no target bar): add an
explicit note that if the dev directly asks for remaining-hours context, the sanctioned answer is
a SEPARATE supplemental fetch for the actual Monday-to-now range (existing entries only, summed
for real, never assumed), rendered as an additional small section clearly labeled as sourced from
that supplemental fetch rather than folded into the gated headline. Never answer the question by
projecting/guessing from the partial window already in hand - that's exactly the 905 bug.

## Acceptance

- SKILL.md step 9a names this pattern explicitly, so a future run doesn't have to reinvent it or,
  worse, fall back to guessing from the partial window on hand.
- The gate itself (no target bar unless the window covers a full Mon-Sun week) is unchanged - this
  only covers the dev-initiated exception path.

## Notes

- Reproduced 2026-09-25, zng-app, `/clockify-reconciliator zirtue` for "yesterday" - second time in
  two days, so this is a recurring ask and not a one-off. The gate again correctly suppressed the
  target bar on the single-day window, the run presented the Thursday-only plan, and the dev's answer
  to the approval card was to reject the whole framing: *"this is bad... i need to see the full week so
  i know how many more hours we are meant to say i worked"*.
- Handled the same improvised way (separate real fetch for Mon 00:00 to now, summed for real, nothing
  assumed on unfetched days), but the stronger reading after two occurrences is that the dev wants the
  week context by DEFAULT on a Reconstruction run, not as an exception path he has to ask for. Worth
  considering as part of the fix: when the config sets `weekly_target_hours` and the mode is
  Reconstruction, widen the presentation to the containing Mon-to-now week automatically (still one
  real fetch, still no assumed days) while leaving the WRITE scope at the window the dev named. That
  would have skipped a full wasted proposal-and-preview cycle here.
- **Reproduced a third time, 2026-09-30, zng-app, `/clockify-reconciliator zirtue` for "today".** Zero
  Clockify entries existed for today, so this was effectively a zero-entry Reconciliation run (not
  named "Reconstruction" but functionally the same shape). Rendered the first card scoped to today
  only (window resolved in step 3), same mistake as the first two occurrences. Dev's reaction: "do you
  really not see anything wrong here? broski... you didnt show me the whole week." Fixed ad hoc the
  same way again: a second real fetch for Mon 00:00-to-now, confirmed NOT stale via a re-fetch (the
  first attempt returned a stale prior-window response per step 4's integrity-check warning - worth
  noting this stale-response risk hit on exactly the kind of ad-hoc supplemental fetch this todo
  documents), then rendered all three days with the full `weekly_target_hours` ring since the
  Mon-to-now window legitimately passed the full-week gate. This wasted a full proposal/preview/reject
  cycle for the third time running.
- **Three occurrences (2026-09-24, 2026-09-25, 2026-09-30) is no longer "worth considering as part of
  the fix" - it's the fix.** The exception-path framing this todo originally proposed (document the
  supplemental-fetch pattern for when the dev asks) is now clearly the wrong shape: the dev has never
  once wanted the narrow single-window card and always corrects to the full week when shown one. The
  Approach below should change from "document an opt-in exception path" to "make the Mon-to-now
  supplemental fetch step 9a's DEFAULT presentation whenever the resolved window (step 3) is narrower
  than the current work week" - still one real fetch, still zero assumed days, still leaving the WRITE
  scope exactly at whatever window the dev actually named (today/yesterday/explicit range) - only the
  VISUAL widens by default. Not implemented live this session (no explicit "fix the skill" instruction
  from the dev this time, unlike the dual-subagent-check change made the same session, so it stayed a
  todo per the global no-unprompted-global-edits rule) - but the next session touching this skill
  should treat this as ready to implement, not still open for debate.
- **Reproduced a fourth time, 2026-10-02, zng-app, `/clockify-reconciliator` for "yesterday".** The run rendered a Thursday-only card although it had already fetched the whole week; the dev: "you did a bad bad thing... you didnt show me the whole week in the preview... why?". Re-rendering from the existing week fetch fixed it in one step. Four occurrences now, still ready to implement as the default.
