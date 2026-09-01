<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=5, reconfirm-count=3, content-hash=047933f0 -->
# Let a pure-relay turn end without forcing a visible chat reply

**Type:** skill-improvement
**Origin:** ai

## Goal

The Stop-hook contract currently requires every turn to produce a chat-visible reply. When a turn's
only input was a repo-coordination-channel message that needed no action, that requirement turns
"nothing to say" into a bubble. Let such a turn end with a quiet status-only acknowledgement instead.

## Context

Surfaced from `claude_conductor`'s backlog todo 698 during a `/mega-todos` run on 2026-08-20. The
measured incident there: a repo-channel wake produced **7 near-identical reply bubbles and burned
roughly 20k tokens**, and most of those messages were addressed to a different peer session
entirely. Numbers are quoted from that todo, not re-measured here.

That todo listed three candidate fixes. Two of them (targeted `post_message` addressing, and
debouncing idle delivery so near-simultaneous posts coalesce into one wake) are pure Rust inside
`claude_conductor` and are being built there. This is the third, and it is NOT that repo's to build:
it changes the forced-reply contract, which lives in this global tree.

Joe's answer when asked why not do all three (2026-08-20): do them all, with the split above.

## Approach

1. Find where the forced-reply requirement is actually enforced. Read the Stop-hook implementation
   under `hooks/` and whatever `TURN_STATUS_PROMPT`-style guidance names it, rather than assuming a
   single site. **Do not write the change before naming the enforcing file:line.**
2. Define what makes a turn "pure relay" narrowly enough to be safe: its only input was a
   repo-channel / peer message, AND the model produced no new information or explicitly flagged
   "no action needed". Both conditions, not either.
3. Let that case end with a status-only acknowledgement (no `send_message` call), leaving the turn
   status itself as the record that it ran.

## Acceptance

- A repo-channel wake that genuinely needed no action ends with no new chat bubble.
- A turn that DOES have something to say still cannot end silent - this is the whole risk of the
  change and needs a real test, not an eyeball.
- The two-condition gate is tested for the near-miss case: a relay turn that DID produce new
  information must still be forced to reply.

## Notes

- Real downside, stated so a future session weighs it rather than rediscovering it: relaxing "a turn
  must produce a visible reply" can silence a turn that genuinely had something to say. That is the
  opposite failure and it is worse than a redundant bubble, because it is invisible. This wants an
  attended session, not an unattended batch run.
- Sibling work lives in `claude_conductor`'s todo 698, which carries the same decision block.
