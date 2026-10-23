<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1193 is about the close_session MCP call order, not the digest step's sessionId -->
# close Phase 3 session-digest step needs a sessionId that short sessions never resolve

**Type:** task
**Origin:** ai

## Goal

`/close` Phase 3 step 4 can always run `recall.py digest-save`, including for a short session.

## Context

Found by the 2026-10-23 loop-todos cycle-1 `/code-check` (fresh subagent) over `8347382..HEAD`.
`skills/close/SKILL.md:233-239` (step 4, added for todo 1152) says to use "the sessionId the
Transcript grounding step resolved". That step (`:120-131`) is headed "(long sessions only)" and says
to skip it under ~500 transcript lines, so a short session that made a decision has no resolved id
and the digest step cannot run as written.

## Approach

Make step 4 resolve the id itself via grounding step 1 (`~/.claude/sessions/*.json`, cwd match,
newest `startedAt`) even when the rest of grounding is skipped.

## Acceptance

A dry read of `/close` gives a short session a concrete way to get its sessionId for `digest-save`.

## Notes

- Done by /loop-todos cycle 2 on 2026-10-23: close SKILL.md Phase 3 step 4 resolves the sessionId via Transcript grounding step 1 even when grounding is skipped for a short session.
