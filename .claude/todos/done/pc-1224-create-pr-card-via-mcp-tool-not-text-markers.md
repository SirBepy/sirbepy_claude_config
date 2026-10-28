<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/394 and done/1067 settled HOW the text markers are parsed; this replaces the text markers entirely after a new 2026-10-23 cause (markers swallowed into a thinking block) -->
# /create-pr: deliver the Conductor PR card through the new MCP tool, not `<cc-pr-*>` text markers

**Type:** task
**Origin:** dev

## Goal
In Claude Conductor, `/create-pr` step 4 shows the PR card by calling the app's PR-preview MCP tool instead of printing the three `<cc-pr-title/body/commits:...>` lines as assistant text.

## Context
- Joe, 2026-10-23, in claude_usage_in_taskbar's todo #1149 chat: picked "New MCP tool for the card".
- Root cause (claude_usage_in_taskbar `.claude/todos/1149-*.md`, 2026-10-23 note): on CLI 2.1.304 / Opus 5.5 the full marker block with long base64 lines lands in the transcript as a `thinking` block (stored as a one-line summary), not a `text` block, so Conductor's parser never sees it. Short marker lines still land as text. The same block worked on CLI 2.1.283.
- Blocked on the app half: claude_usage_in_taskbar #1149 adds the tool. Read that todo for the tool's final name and params before editing.

## Approach
1. After #1149 ships, rewrite `skills/create-pr/SKILL.md` step 4's "Claude Conductor specifically" part: call the tool with title, raw body and commits, no base64.
2. Keep the plain-markdown preview render for non-Conductor sessions.

## Acceptance
- A real `/create-pr` run in Conductor shows the card.

## Notes

- Done 2026-10-25 (af0dd983) from claude_usage_in_taskbar /loop-todos with Joe's in-session OK: step 4 calls mcp__cc_conductor__pr_preview in Conductor; a live pr_preview call returned 'PR preview card shown in chat'.

## Decided

Decided by /auto-do-todos on 2026-10-23.

- [x] [TOOLING] Rewrite create-pr step 4 now? - decided **park until claude_usage_in_taskbar todo 1149 ships the PR-preview MCP tool**, because no such tool exists in this session and a guessed name would need redoing.
