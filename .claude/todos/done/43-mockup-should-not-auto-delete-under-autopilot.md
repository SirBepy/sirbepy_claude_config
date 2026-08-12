<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=2, content-hash=02d97841 -->
# /mockup: don't auto-delete the scratch route when the dev was never there to look

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `/mockup` from destroying the thing it was asked to produce when it runs
unattended. Its auto-delete step assumes the dev watched the preview live; under
`/autopilot` nobody did.

## Context

Skill file: `C:\Users\tecno\.claude-fibo\skills\mockup\SKILL.md`, step 7:

> "Stop, and auto-delete the real-component branch's scratch route once the dev
> stops iterating. Once the dev has seen the preview, the skill's job is done...
> Delete the scratch route/files and stop any process you started for them
> automatically, without asking, once the dev is done looking - an orphaned scratch
> route with no disposal step is the predictable failure mode."

The reasoning is sound when the dev is present. It breaks when he is not.

**Incident, 2026-08-05 (fibo/frontend2).** `/mockup` ran inside an `/autopilot`
session to compare three mobile layouts for `/canonical-items`. The route was
built, screenshotted, and deleted per step 7, all while the dev was AFK. His very
next message after the run was:

> "can you tell me how i can view those mockups in a tab?"

The answer was that he could not: only PNGs survived. The whole point of a mockup
is to be looked at interactively, at real widths, and the skill had already thrown
that away before he saw it once. Rebuilding it costs another full subagent run.

Note the trigger condition step 7 keys off - "once the dev is done looking" - is
unobservable in an unattended run. There is no signal, so the step fires
immediately, which is the worst possible reading of it.

## Approach

Make the disposal conditional on whether a human actually saw it. Options, in
rough order of preference:

1. **Skip the delete when running unattended** (`/autopilot`, or any run where the
   dev has not responded since the preview went up), and instead file the scratch
   route's paths into `.claude/todos/` as a cleanup task, so the orphan is tracked
   rather than either leaked or destroyed. This keeps step 7's real goal - no
   silent orphan - while preserving the artifact.
2. Keep deleting, but first copy the scratch files somewhere durable (not
   `.for_bepy/`, which `/close` purges) so the route can be restored in one step.
3. At minimum, have the run's final summary state the exact command or diff needed
   to bring the route back, so the dev is not told "it's gone, I can rebuild it"
   with no path forward.

Also worth fixing in the same pass: the skill sends screenshots to
`.for_bepy/screenshots/`, which `/close` purges by design. Any mockup whose PNGs
are the decision artifact (see todos `214` and `216`, both of which cite those
files as the thing to decide from) is therefore on a timer nobody declared.
Consider a durable location for mockup output specifically.

## Acceptance

- A `/mockup` run under `/autopilot` leaves either the live route or a documented
  one-step path to restore it.
- A `/mockup` run with the dev present behaves exactly as it does today.
- The skill states, in step 7, which signal it uses to decide the dev "is done
  looking", rather than leaving it to interpretation.

## Notes

Do not solve this by simply never deleting: the orphaned-scratch-route failure
step 7 guards against is real, and a dead route left in `App.tsx` did get
committed by accident in this project's history. The fix is to make disposal
conditional and tracked, not to drop it.

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 218; renumbered to 43 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: in `mockup/SKILL.md` step 7, make deletion conditional instead of unconditional -
  skip it when running unattended (no dev response since the preview went up), and file the scratch
  route's path into `.claude/todos/` as a cleanup task instead. This is option 1, the todo's own
  stated preference. This was produced by a strict second-pass re-triage that specifically asked
  whether a defensible answer exists without the dev; it concluded yes. Not executed only because
  the session ended.
- completed, commit e6f2199
