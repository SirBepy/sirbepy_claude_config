<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=6, reconfirm-count=3, content-hash=8e918ea8 -->
# Settle whether Conductor's card parser reads raw assistant text or only send_message payloads

**Type:** task
**Origin:** ai

## Goal

Establish, by observation in a live Claude Conductor session, which channel the in-app card parser
actually reads, then collapse `skills/create-pr/SKILL.md` step 4's two-branch workaround down to the
one branch that is actually true.

## Context

`create-pr-preview-card-never-renders` (archived 2026-08-19, commit `2cca26d`) could not be fixed
outright because the fix SHAPE depends on an external fact nobody has established. That todo's
builder deliberately wrote both resolutions into the skill rather than guessing one, and flagged the
unresolved fact for follow-up.

The conflict: `skills/create-pr/SKILL.md` step 4 requires the marker emission to be the FINAL action
of its turn with no tool call after it. In Conductor that is unsatisfiable, because
`report_turn_status` is mandatory on every turn. So the preview card never renders, which is what
the dev originally reported.

The two candidate resolutions, currently BOTH documented:

- If the parser reads raw assistant text, relax the no-tool-call-after rule to exempt
  `report_turn_status`.
- If it reads only `send_message` payloads, emit the markers through `send_message` instead.

Emitting both a card and an inline body would double-render, so this cannot be resolved by doing
both defensively.

## Approach

1. In a live Conductor session, run one real `/create-pr` (or a minimal reproduction that emits the
   same markers) and observe which emission actually renders the card.
2. Keep the branch that matches the observation. DELETE the other, including its explanatory prose,
   so the skill stops carrying a conditional nobody can evaluate at read time.
3. Note the observed behaviour with an absolute date, since this is harness behaviour that can
   change under a Conductor update.

## Acceptance

- `skills/create-pr/SKILL.md` step 4 states one rule, not a fork.
- The preview card demonstrably renders on a real run.
- The observation and its date are recorded where the next reader will find them.

## Notes

- This needs a live Conductor session, so it cannot be closed from a headless or subagent context.
- Relocated to 911 in claude_usage_in_taskbar (remote: SirBepy/claude_conductor) via /mega-todos 2026-09-04, on Joe's suggestion. The observation it needs can only be made inside a live Conductor session. NOTE: the fix still lands in this repo at skills/create-pr/SKILL.md:219-237 - the relocated todo says so and asks that the observed answer be recorded precisely enough to apply here without re-observing. Also flagged there that text markers are being retired in favour of the MCP API, which may moot both branches.

## Open questions

Written by /mega-todos on 2026-09-04. The next run opens with these.

- [ ] [TOOLING] `skills/create-pr/SKILL.md` documents two contradictory branches for how Conductor parses preview-card markers, and resolving it needs one real `/create-pr` run inside Conductor to observe which is true. A subagent cannot observe that. Options: run `/create-pr` once in a Conductor session and let Claude delete the losing branch / delete the branch you believe is wrong now / leave both documented. Recommended: run it once. The observation is cheap and the file currently contradicts itself.
