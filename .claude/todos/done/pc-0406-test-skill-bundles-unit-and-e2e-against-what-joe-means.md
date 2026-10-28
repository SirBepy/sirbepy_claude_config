<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /test bundles unit + e2e, but Joe means "drive it by hand"

**Type:** task
**Origin:** ai

## Goal
Stop `/test` from firing a long automated suite when Joe wanted the app installed
and clicked through.

## Context
2026-08-19, revaire-mobile REV-5312. Joe asked for an e2e test. `/test`'s Step 4
routes Flutter e2e to the automated suite, so Claude ran Patrol twice (12 min, then
again). His reply: *"mind explaining why the fuck youre running the patrol tests
again? ... i was trying to ask you to run the tests by clicking around and making
sure everything looks good"*. He then said: *"now im starting to think myb
combining unit tests and e2e into one skill was a mistake"*.

The skill is not wrong about what it does, it says plainly that `/test` means unit
AND e2e. The gap is that "e2e" resolves to a test runner, and Joe's "e2e" means a
human-style pass over the running app with screenshots.

`~/.claude/skills/test/SKILL.md` Step 4, and the Flutter row of Step 1's table.

## Approach
Either split the verb (`/test` = automated, something else = hand-driven), or make
Step 4 ask which he wants when the project has both an automated suite and a
device/emulator available. A third option: make the Flutter e2e row prefer an
install-and-drive pass and treat the Patrol suite as opt-in.

Whatever shape wins, `/test` should never consume 12 minutes of mocked suite before
Joe sees the change on a screen.

## Acceptance
Invoking `/test` on a Flutter repo with an emulator attached results in the app
being installed and driven, or in one question that settles which he meant, and
never in an unattended automated-only run reported as the answer to "e2e".

## Notes

- Dropped via /cleanup-todos 2026-08-27: premise dead. /test no longer routes Flutter e2e to Patrol - skills/test/SKILL.md:28 is `fvm flutter test` (unit only), /e2e was split out 2026-08-19 (skills/e2e/SKILL.md:13 "/test stays fast-checks-only, this owns everything that drives a real UI"), and Patrol appears 0 times anywhere under skills/flutter-e2e/. That is exactly the fix this todo proposed, already shipped. Origin ai, archived without a confirm gate per the skill origin rule.
