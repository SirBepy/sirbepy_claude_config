<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=3, reconfirm-count=1, content-hash=d7d93228 -->
<!-- duplicate-checked: done/331 and done/348 are the closest neighbours and neither covers this. 331 built the guard (omissions were invisible until /close swept); 348 created refs/builder-preamble.md so there was something to paste FROM. Both are landed. This one asks why, with the guard AND the paste source both in place, the block still gets left out of the first draft. -->
# 1006 - Always paste the builder-preamble block on the first draft of an Agent dispatch, not after a rejection

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop losing a round-trip to `hooks/dispatch-preamble-guard.py` every time an Agent dispatch is
drafted without the staging line / `run_in_background` + `FORBIDDEN` line / screenshot marker
already in the prompt.

## Context

2026-09-03, `/clockify-reconciliator` run in zng-app: dispatched 3 parallel `general-purpose`
agents (a time-math audit, a commit-coverage audit, a description-accuracy audit) as read-only
verification passes. All 3 were rejected in one message by `dispatch-preamble-guard.py` for
missing the staging line and the `run_in_background`/`FORBIDDEN` marker, even though `READ-ONLY
DISPATCH` (the screenshot-exemption marker) was already present. Had to redraft and resend all 3
with the full canonical block pasted in. The global CLAUDE.md section "Subagent-Driven vs Inline
Execution" already states this applies to "even an ad-hoc one with no skill in the loop" - the
rule was known, just not applied on the first draft.

## Approach

No code change - this is a standing personal-habit gap, not a missing rule. Options considered:

- Add a pre-dispatch checklist step to a personal workflow doc: before calling `Agent`, grep the
  draft prompt for the three markers `hooks/dispatch-preamble-guard.py` checks
  (`Stage your changes`/`Leave all changes unstaged`, `run_in_background` + `FORBIDDEN`,
  `.for_bepy/screenshots/` or `READ-ONLY DISPATCH`) before sending, rather than discovering the
  rejection after the fact.
- Simplest fix: default to pasting `~/.claude/refs/builder-preamble.md`'s literal block into every
  Agent dispatch prompt from the start, verbatim, the same way `/close`'s own doctrine already
  describes - treat it as boilerplate to always include, not a rule to remember to apply.

Re-scope to the mechanical half only: always paste the preamble block verbatim on the first draft,
rather than adding another line of prose telling a future session to remember.

## Acceptance

- Future Agent/Task dispatches in this or other repos include the required markers on the first
  send, with zero `dispatch-preamble-guard.py` rejections logged in a session.

## Notes

Low-stakes, cosmetic friction (cost was a few extra tool calls, not incorrect work) - filing this
mainly so the pattern doesn't recur silently across sessions.

- ~~Dropped via /cleanup-todos 2026-09-05: the rule already exists, per `~/.claude` todo 773, done in `fc4ec4b`.~~ **That drop was wrong and this todo was restored 2026-09-06 after an adversarial re-check.** 773 answered discoverability: is the rule written down. It is, and this file's own Context already said so, explicitly pre-empting that objection ("the rule was known, just not applied on the first draft"). This todo asks the enforcement question instead: why documenting it did not stop the miss from recurring. The archive answered a question 773 had already closed and left this one untouched.
- Relocated from todo 125 in `c:\Users\tecno\Desktop\Projects\zng-app` via /cleanup-todos 2026-09-24: the subject is `hooks/dispatch-preamble-guard.py` and the global CLAUDE.md dispatch rule, not zng-app code. It was only ever logged from zng-app sessions because that is where the dispatches happened.
- Duplicate of 1028 - merged during /cleanup-todos 2026-10-05; read-before-drafting evidence folded into 1028's Notes.

## Occurrence 2, 2026-09-15 (zng-app, sc-55568 verification session)

Recurred exactly as described, and this is now the second logged instance, which is the escalation
signal the Notes above named ("if it keeps happening after this todo is read once, that's a signal
the checklist approach isn't sticking").

Four `general-purpose` agents were dispatched in one message as read-only verification passes.
All four were rejected together by `dispatch-preamble-guard.py` for the same two markers as
occurrence 1: the staging line and `run_in_background` + `FORBIDDEN`. `READ-ONLY DISPATCH` was
again present, again not sufficient. Cost: one rejected round trip plus two reads of
`refs/builder-preamble.md` to recover the exact wording, then a full redraft of all four prompts.

Note the shape: both occurrences were READ-ONLY dispatches, where a staging line reads as
irrelevant and is therefore the easiest marker to omit. That is the specific trigger worth fixing
mechanically. Later in the same session a fifth dispatch (the `/code-check` reviewer) carried the
full block on the first send and passed, but only because the rejection had just happened.

Prose has now failed twice. Prefer the mechanical option: a snippet or a guard-side hint that emits
the required block, rather than a third reminder to remember it.

## Counter-observation, 2026-09-24 (zng-app, /cleanup-todos run)

Four read-only `general-purpose` dispatches in one message, all four passed the guard on the first
send. The difference from occurrences 1 and 2 was mechanical, not motivational: the orchestrator
read `refs/builder-preamble.md` in the same turn it drafted the prompts, and pasted the block from
that tool result rather than from memory.

That is weak evidence for the "simplest fix" option above and against the checklist option. It is
one sample and a deliberate one, so it does not close this todo - but it does narrow what the fix
should look like. The failing shape is drafting a dispatch WITHOUT the ref file already in context;
the passing shape is reading it first. A guard-side hint that emits the block on rejection, or a
snippet auto-imported before the first dispatch of a session, both attack that seam directly.
