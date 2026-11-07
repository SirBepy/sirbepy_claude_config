<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1193 (done) is about close_session ordering in Phase 6 (the kill script); this is a new "started" signal at Phase 1 so the host marks Closing at the right moment. The other hits only share vocabulary. -->
# /close tells Conductor when its Phase 1 starts, so the Closing badge no longer keys on the prompt text

**Type:** task
**Origin:** ai
**Summary:** The close skill should emit a "started" signal when Phase 1 begins so Conductor marks a chat Closing at that moment instead of whenever a turn's prompt starts with /close.

## Goal

Conductor marks a chat "Closing" from a signal the `/close` skill emits when its own phases start, not from the prompt heuristic `turn_is_close` (`starts_with("/close")` in the Conductor repo's `src-tauri/src/daemon/pump/close.rs`). Today a trailing `/close` (gate-chat spawn prompts end with it) never shows Closing, and a leading one shows Closing during Phase 0 work and across a question card.

## Context

Filed from the Conductor repo (`claude_usage_in_taskbar`) todo pc-1526, Part B. Part A (a `/close` turn that ends on a question no longer sets close-failed) landed in Conductor commit e3c1106f. Part B needs this skill-side change, which a project session may not make:

- `skills/close/SKILL.md` "Host app integration" currently documents "host marks Closing when a /close turn starts" (~lines 68-70 at filing time).
- Conductor side (separate, in its own repo): add an optional `close_session(stage="started")` MCP call that sets `closing`, keep the prompt heuristic only for `/close --now`.

## Approach

1. In `skills/close/SKILL.md`, at the start of Phase 1 (after Phase 0's task finishing), call `close_session` with `stage: "started"` when that MCP tool exists (skip silently when it does not, e.g. a plain terminal session).
2. Update the "Host app integration" paragraph to say the host marks Closing on that signal, with the prompt heuristic only for `--now`.
3. Then the Conductor repo adds the `stage` parameter and drops the heuristic for the non-`--now` case.

## Acceptance

- A `/close` that finishes a task over two turns, with a question card in between, shows neither Closing nor close-failed before its Phase 1 starts.
- A trailing `/close` shows Closing once Phase 1 starts.
- `skills/close/SKILL.md` documents the signal and the `--now` exception.

## Completion note

Skill side done: Phase 1 now opens with `close_session(stage: "started")` (skipped when the tool lacks a `stage` parameter or does not exist) and "Host app integration" documents the signal and the `--now` exception. Verify only: the first two Acceptance bullets (Closing badge timing) need a live Conductor build with `stage` support; its `close_session` schema lists `stage` as of 2026-11-07.
