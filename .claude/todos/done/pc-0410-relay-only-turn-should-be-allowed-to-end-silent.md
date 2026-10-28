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
- **2026-09-03, countoff session `598a9d17`: evidence that step 1's premise may be false, i.e. the
  forced-reply requirement is NOT actually enforced anywhere.** Three consecutive turns of a long
  build ended with `report_turn_status` and no `mcp__cc_conductor__send_message`, and nothing
  blocked them. From the dev's side the session looked hung; his messages, in order: "i gave u the
  5 answers right?", "are you stuck??", "do you see any of my msgs?", then "WHAT THE FUCK IS GOING
  ON WHAT THE FUCK IM SO FUCKING PISSED HOLY SHIT". The work was on track the whole time; the cost
  was entirely a missing tool call. Note the em-dash Stop hook DID fire in that same session
  (it caught a `post_message` arg), so Stop hooks were running - there just is no send_message one.
  This inverts the shape of this todo: if there is no enforcement, the "opposite failure" in the
  bullet above is not hypothetical, it is the CURRENT default, and the work is to BUILD the guard
  with the relay exception baked in from the start, not to relax an existing one. The asymmetry
  that causes the miss is worth encoding: `report_turn_status` is prompted explicitly as the last
  action of a turn and so survives under load, while `send_message` carries equal obligation with
  no prompt, so it is the one that gets dropped. Resolve step 1 before assuming either direction.
- Fixed in c84debb: hooks/send-message-stop-guard.py blocks a turn only after 3 consecutive Conductor-signal turns with no send_message, so a quiet turn or two passes and a fully silent stretch does not. The relay exception is implemented and tested, including the near-miss case where a relay turn also edits files and therefore gets no exemption.

## Open questions

Written by /mega-todos on 2026-09-04. The next run opens with these.

- [ ] [ARCH] The 2026-09-03 countoff session proved there is NO enforcement of `send_message` at all, which inverts this todo: the relay exception is the current default, not an over-strict rule to relax. Build the guard from scratch with the exception baked in, or leave it unenforced? Options: build a Stop-hook guard requiring `send_message` unless the pure-relay exception applies / leave it unenforced and rely on the prompt / narrow it to long autonomous runs only. Recommended: build it. `report_turn_status` survives under load because it is prompted explicitly as the last action of a turn; `send_message` carries equal obligation with no prompt, which is exactly why it gets dropped.
