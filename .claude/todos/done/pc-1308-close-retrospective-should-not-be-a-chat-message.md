<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md --><!-- duplicate-checked: hits by filename are create-pr bypass, garbled voice input, screenshot deletion, peer-channel hook and relay-only turns; none is about close-out text reaching Joe, they share only the words stop, close and message -->
# /close's retrospective and bookkeeping footer should stop reaching Joe as a chat message

**Type:** task
**Origin:** dev
**Summary:** A clean `/close` tells Joe nothing he has to read: no retrospective bubble and no bookkeeping footer, only a real miss reaches him.

## Why

Joe picked this on 2026-11-04 in the claude_usage_in_taskbar message-kinds brainstorm (its todo pc-1592). From a sample of 260 real messages, 3 were retrospectives and about 12 close-outs carried a footer like "0 memory writes, 4 todos written, 0 screenshots, chain: none, closing: yes". He does not read them.

## Goal

A clean close sends no retrospective or bookkeeping text to Joe. A real miss, or something he must act on, still reaches him. In Conductor that goes through `send_message` with a kind: a do_this or a report row in `your_move`.

## Context

- `skills/close/SKILL.md` Phase 1 is the retrospective, and line 282 is the bookkeeping footer format.
- That project's `send_message` now requires `kind` (answer, report, blocker, do_this, plan, rating, correction, call, handoff, artifact, discovery, ack), and `ack` is not drawn. See `src-tauri/src/mcp/tool_schemas_coordination.rs` there.
- Skills that prescribe message wording may need the same check: `/commit`'s push report and `/gate-chat`, whose reports read like the wordy report Joe objected to. UNVERIFIED which ones, would check each SKILL.md.

## Acceptance

- A clean `/close` in a Conductor chat shows Joe no retrospective bubble.
- A close with a real miss still tells him, in one line naming the miss.

## Completion note

Done in `skills/close/SKILL.md`: in a Conductor-hosted chat (the `send_message` tool exists) Phase 1 prints nothing and Phase 4 sends no counter; only a real miss goes out as one `report` or `do_this` line. A plain terminal keeps today's output. Verify only: seeing no bubble needs a live Conductor close. Left alone (outside the lane that touched it): `skills/respawn/SKILL.md:115` still says "Print the one-line counter"; `/commit`'s push report and `/gate-chat`'s report wording were not audited, so the todo's UNVERIFIED sibling-skill question stays open for them.
