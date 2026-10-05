<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=6, reconfirm-count=1, content-hash=02823346 -->
<!-- duplicate-checked: 394 (done/) asked the same question and was relocated to claude_usage_in_taskbar todo 911, which settled it on 2026-10-02. This is the skill edit 394 said still lands here. -->
# create-pr: drop the "parser only reads send_message" marker branch

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/create-pr/SKILL.md` step 4 states one way to emit the PR card markers in Claude Conductor,
instead of a two-branch conditional hedging on how Conductor parses them.

## Context

Follow-on to done/394, which was relocated to claude_usage_in_taskbar todo 911 because the answer
needed Conductor. 911 settled it on 2026-10-02 (/loop-todos cycle 1) from Conductor's code: the
`<cc-pr-title:>` / `<cc-pr-body:>` / `<cc-pr-commits:>` markers are parsed in the FRONTEND from raw
assistant text blocks - `detectPrPreviewToken` (`src/shared/chat/chat-classifiers.ts:58-80`), called
from the `case "assistant":` branch of `src/shared/chat/chat-transforms.ts` (~294-301), gated only on
the message being finalized (`!m.streaming`). The `send_message` path is a separate `case "message":`
branch that never runs the detector. A trailing `report_turn_status` tool call renders as its own
message and does not block the card. Pinned by `tests/chat-transforms.test.mjs`
("renderMessage - PR preview card ...", commit 5028c302 in claude_usage_in_taskbar).

## Approach

In `skills/create-pr/SKILL.md` step 4 (394 cited lines 219-237; re-find them), delete the second
branch ("If the parser only reads `send_message` payloads: emit the three marker lines as the body
of a `send_message` call instead") and its explanatory prose. State plainly: Conductor's card parser
reads raw assistant text, so emit the markers as plain text in the final reply; `report_turn_status`
is exempt from the "no tool call after it" rule. Record the 2026-10-02 date and the test as the
evidence, since a Conductor update could change it.

## Acceptance

- Step 4 has a single instruction for Conductor, citing the claude_usage_in_taskbar test above.
- `python ci/run_all.py` green in `~/.claude`.
