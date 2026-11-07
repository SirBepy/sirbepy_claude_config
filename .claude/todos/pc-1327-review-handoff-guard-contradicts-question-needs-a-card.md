<!-- duplicate-checked: hits share only stop/question vocabulary (close phase signal, ticket state reader, AUQ labels, AUQ proposals, dispatch preamble), none about these two stop rules conflicting -->
# The review hand-off stop guard contradicts the daemon's question-needs-a-card rule

**Summary:** `hooks/send-message-stop-guard.py` demands status question after show_preview or write_draft, but Conductor's stop verdict then rejects status question with no card up, so each draft or preview forces a filler question card.
**Type:** skill-improvement
**Origin:** ai

## Observed (2026-11-05, zng-app chat 0a3b4277)

Three times in one session:

1. A turn called `show_preview` and reported `done`. `send-message-stop-guard` blocked: "A turn waiting on his review is not done: call report_turn_status with status question".
2. A turn called `write_draft` and reported `question`. Conductor's `src-tauri/src/daemon/hooks_server/stop_verdict.rs` blocked: "You reported status 'question' but no ask_user_question card is up".
3. The only way through both was a question card Joe did not need, such as "re-check or post it?".

Joe's own edits and rewrites hit this too: a draft in his exact words still counted as something to review.

## Approach

`REVIEW_HANDOFF_SUFFIXES` at `hooks/send-message-stop-guard.py:106`, and its check near line 121. Change the guard so a turn that shows a preview or draft and needs no decision may end as `done`, or have it point at the card explicitly so the two rules agree. Update `hooks/test_send_message_stop_guard.py`. Conductor's rule came from claude_usage_in_taskbar pc-1593, so keep that one.
