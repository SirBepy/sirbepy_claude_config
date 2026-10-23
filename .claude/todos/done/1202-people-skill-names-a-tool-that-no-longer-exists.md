<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits share only generic words (skill, call, tool); grep of backlog and done/ for find_person/remember_person found nothing -->
# /people skill tells Conductor chats to call find_person / remember_person, but the tool is one `person` tool

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/people/SKILL.md` names the MCP tool Conductor actually exposes, so a chat following the
skill calls it on the first try.

## Context

Found 2026-10-19 by a builder in the claude_usage_in_taskbar auto-do-todos run (its todo 1214).
`skills/people/SKILL.md` lines 20, 24, 25 and 45 say `find_person` / `remember_person`. Conductor
exposes a single `person` tool with an `action` enum of `find` / `remember`
(claude_usage_in_taskbar `src-tauri/src/mcp/tool_schemas_workflow.rs:194-215`,
`src-tauri/src/mcp/dispatch.rs:307-313`). Since commit 4333fe69 in that repo, `action: remember`
also raises a permission card when auto-accept is off, while `find` stays prompt-free.

## Approach

Replace each `find_person` with "`person` with `action: find`" and each `remember_person` with
"`person` with `action: remember`", keeping the argument names (`join_project`, `alias`, `new`).
Optionally note that `remember` may show a permission card.

## Acceptance

- `grep -n "find_person\|remember_person" skills/people/SKILL.md` returns nothing.
- The skill still reads correctly for a non-Conductor session (the vault-file fallback is unchanged).

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): people skill calls the single person tool with action find/remember (join_project, alias, new), checked against the live mcp__cc_conductor__person schema.
