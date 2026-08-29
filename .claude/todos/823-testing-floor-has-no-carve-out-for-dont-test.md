<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=8, reconfirm-count=2, content-hash=53c79a84 -->
<!-- duplicate-checked -->
# The testing floor has no carve-out for Joe saying "don't test"

**Type:** skill-improvement
**Origin:** ai

## Goal

Give global `CLAUDE.md`'s "Testing & verification floor" an explicit rule for what happens when
Joe tells Claude not to run the checks, and for how long that instruction holds.

## Context

zng-app session, 2026-08-27. Joe said, mid-session: *"when youre done, dont test it, just tell me
and then /close"*. I treated that as scoped to that single turn. Several turns later I ran
`fvm flutter test` (full suite) again as part of the floor, and he interrupted it twice:

> "who told you to run the full test suite, please tell me"

> "please tell me when did i tell you to run the full test suite"

He never had. The honest answer was "your own global rule told me to", which is exactly the
problem - the rule reads as unconditional:

> Before claiming done or handing to Joe: run every FAST check the project HAS (typecheck, unit,
> lint, build) - all must pass. **No size exemption**; a one-line edit gets the same floor as a
> rewrite. Never skip silently because something "looks small."

Every escape hatch it offers is about the change being too small or untestable. There is no clause
for the dev explicitly declining the checks, so the literal reading is that Claude runs them
anyway - which is what happened, and it reads as ignoring him.

Related but not the same: this repo's `feedback_background_the_slow_checks` memory (zng-app scope)
already says to background slow checks and scope `analyze` to changed dirs, after a similar
complaint on 2026-08-24. That one was about blocking the turn. This is about running them at all.
Two complaints, three days apart, same underlying rule.

## Approach

Edit the "Testing & verification floor" section of `C:\Users\tecno\.claude-personal\CLAUDE.md`.
Add a clause along the lines of:

- A "don't test" / "don't run the tests" from the dev is a **standing instruction for the rest of
  the session**, not a one-turn exemption. It is not re-armed by a new task in the same session.
- When it is in force, say plainly what was NOT run when handing over, so the gap is visible
  rather than silent. The floor's own "say so explicitly rather than skipping quietly" principle
  already covers the untestable case; extend the same treatment here.
- Consider distinguishing the cheap checks (typecheck / lint / scoped analyze) from the full unit
  suite. Joe's objection both times was to the **full suite**, not to `analyze`.

Watch for: this must not become a general licence to skip verification. The trigger is an explicit
instruction from the dev, not Claude's own judgement that a change looks safe.

## Verify

- [ ] The section states what an explicit "don't test" does, and for how long it lasts
- [ ] It still requires saying out loud which checks were skipped
- [ ] It does not weaken the default (checks run unless the dev says otherwise)

## Notes

Filed from a zng-app session per global CLAUDE.md's rule that findings about the `~/.claude` tree
belong in this backlog, not the surfacing project's. Not executed there - only filed.
