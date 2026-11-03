<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/1098 is "blocked on Joe reported as working" (a dev physical action); this is a visual or design round handed to Joe for review being reported as done. No open todo covers it. -->
# A turn that hands Joe something to review ends as "question", not "done"

**Type:** skill-improvement
**Origin:** dev
**Summary:** A turn that hands Joe something to review, such as a preview, mockup or draft, ends as "question" instead of "done".

## Why

"you keep being marked done with the way the UI is made. Realistically you should, at that point, mark the chat as 'input needed'" (Joe, 2026-10-26).

## Goal

Every session ends a turn with `report_turn_status(status: "question")`, not `"done"`, when the turn hands Joe something
to look at and judge: a design round in a preview, a mockup, a screenshot, a draft he has to approve.

## Context

- Joe, 2026-10-26, in the dashboard-a projects design chat: "you keep being marked done with the way the UI is made.
  Realistically you should, at that point, mark the chat as 'input needed' because you need me to view something and
  check if it's okay or not". Three design rounds that day ended `done` though each waited on his review.
- The tool's own description already says `question=awaiting the user's input`, so the rule exists; sessions read
  "question" as "a question card is open". Nothing in CLAUDE.md or a hook says a review hand-off counts.
- Joe also floated, for the Conductor app (claude_usage_in_taskbar), separating "input needed / review" from
  "question card" in the sidebar. He did not ask for it to be filed yet; ask him before filing it in that repo.

## Approach

1. Add one line to global `CLAUDE.md` (Communication or Testing & verification): a turn that hands Joe a visual or
   draft to judge ends `question`, never `done`.
2. Consider a Stop-hook check: a turn that called `show_preview`, `/preview`'s post, `SendUserFile` or `write_draft`
   and reports `done` gets a warning.

## Acceptance

- A design session that posts a preview for Joe's review ends its turn with status `question`.
- Turns that finish work with nothing for Joe to judge still end `done`.

## Notes

- Fixed in bcc5080 (Stop-hook half only; the app-side TURN_STATUS_PROMPT and a CLAUDE.md line were not done).
