<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# `/pickup`'s card rule covers a timed-out card but not one that is still pending

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/pickup` Step 4 an explicit branch for "the dev said continue while a question card is still
alive and unanswered", so the timeout branch stops being applied to a case it was not written for.

## Context

Happened 2026-08-18 during todo 351. Four decisions went out on one
`mcp__cc_conductor__ask_user_question` card. The tool returned its normal acknowledgement - *"the
card is now waiting for their answer... end your turn now"* - so the card was alive, not expired.

Joe's next message was `continue i might have interrupted you`, carrying no answers.

`skills/pickup/SKILL.md` Step 4 has exactly three branches: interactive, `--unattended`, and **card
timed out mid-run**. That third branch permits proceeding on any option explicitly badged
recommended when the resulting action is reversible. None of the three describes a card that is
still pending, so the timeout branch got stretched to cover it and work began on all four
recommended options.

Joe's correction one message later was `ask again`. The card was re-sent and he answered it, and
**one of his four answers differed from the recommendation** - he chose "delete them" over the
badged "thin aliases" for the three absorbed Shortcut skills. So proceeding on the badges would
have shipped the wrong shape and needed unwinding.

## Approach

Add a fourth branch to `skills/pickup/SKILL.md` Step 4, before the timeout one so it is read first:

- **Card still pending, dev sends an unrelated or non-answering message** (`continue`, `go`, a
  question about something else). This is NOT the timeout case and NOT permission to proceed on
  recommendations. Re-send the card, or ask which of the pending decisions he wants to skip. The
  distinguishing signal is mechanical, not a judgment call: the timeout branch requires an actual
  MCP idle-timeout error (`sent no response or progress`), so absent that error the card never died.

Word the timeout branch to say so explicitly, since its current text invites the stretch: it should
require the timeout error as a precondition, not merely describe one.

Consider whether `/close` Phase 0 and `/batch-todos` need the same branch; they have the same
interactive-question shape. Check before duplicating, do not assume.

## Acceptance

- Step 4 names the still-pending case and routes it to re-ask, not to proceed.
- The timeout branch states the MCP idle-timeout error as its precondition.
- A reader cannot reach "proceed on recommendations" from a card that never errored.

## Notes

- Filed 2026-08-18 by `/close`.
- The badged recommendations were not a safe default here: 1 of 4 answers went against them.
- Related memory: `reference_question_card_dies_on_timeout`, updated the same day with this case.
