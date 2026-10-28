<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=6, reconfirm-count=1, content-hash=46fbc382 -->
<!-- duplicate-checked -->
# rate-it/iterate-it's flaw-hunt angles have no "parity vs replaced code" check

**Type:** skill-improvement
**Origin:** ai

## Goal

Add a review angle (or a standing checklist item inside the existing angles) to `rate-it/SKILL.md`'s
flaw-hunt rules, used by both `/rate-it` and `/iterate-it`, that explicitly checks whether a proposal
that PORTS or REPLACES existing logic preserves the full behavior of what it's replacing - not just
whether the new code works on its own terms.

## Context

zng-app session 2026-08-22 (Sentry noise-filter fix): `/iterate-it` ran 7 rounds (5 Explore + 2
Polish) converging on a JS-side `addEventProcessor` filter to replace a dead Dart-side `beforeSend`
filter (`lib/shared/sentry_noise_filter.dart`). The old filter matched noise two ways - an exception-
message string list AND a stack-frame extension-URL-prefix check (`chrome-extension://` etc). The
ported JS version only carried the message-string list; the frame-prefix check was silently dropped
during the port.

None of the 7 rounds caught this, across skeptic, misdiagnosis, shippability (x2), steelman, and
alternative-lens angles - because every angle asked "does this proposal work" (compile-correctness,
timing/race conditions, mechanism soundness, live-browser verification), never "does this proposal
cover everything the code it's replacing covered." The gap was caught by the human developer from a
plain side-by-side diff read, not by any review round.

See zng-app's `project_sentry_noise_filter_web_gap.md` memory and commit `e96525e` for the full
before/after. The existing angle rotation is `skeptic â†’ steelman â†’ alternative-lens â†’ shippability â†’
misdiagnosis` (see `~/.claude-personal/skills/iterate-it/SKILL.md` and `rate-it/SKILL.md`'s flaw-hunt
rules) - none of the five is scoped to "compare against the thing being replaced."

## Approach

In `rate-it/SKILL.md`'s flaw-hunt rules (read alongside `iterate-it/SKILL.md`'s angle descriptions):
add an explicit checklist item, applicable whenever the hypothesis under review deletes, replaces, or
reimplements existing code - not a new rotation angle (would dilute the existing 5-angle cycle), but a
standing "if this ports something, diff it" instruction any sub applies regardless of assigned angle.
Concretely: "If P_R deletes or replaces existing logic, read the old implementation's full behavior
(not just its signature) and confirm every branch/check it performed is either preserved in the new
code or explicitly, deliberately dropped with a stated reason - not silently lost in translation."

## Acceptance

- `rate-it/SKILL.md` (or wherever the flaw-hunt rules live) has this checklist item in writing.
- A future `/iterate-it`/`/rate-it` run reviewing a "replace X with Y" proposal explicitly states
  whether Y has full behavioral parity with X, not just whether Y works.

## Notes

Low-frequency but high-cost when it hits: a review process specifically designed to catch this class
of thing (multiple rounds, adversarial angles, live testing) still missed a real coverage regression
because nothing in it was pointed at the comparison. Worth the one-line addition.
- Done via /mega-todos batch 3, commit 34fe173: rate-it Flaw hunt now carries a standing parity check for ports and replacements, read the old implementation's full behavior and confirm every branch is preserved or deliberately dropped with a reason. Kept as a standing instruction rather than a sixth rotation angle.
