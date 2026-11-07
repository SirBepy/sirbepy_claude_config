<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1255 is about brainstorming questions going on the card; it mentions dashboard-a only as the incident repo -->
# Brainstorming exception in global CLAUDE.md names the old repo

**Type:** task
**Origin:** ai
**Summary:** Global `CLAUDE.md` line 72 says "dashboard-a planning talks use `superpowers:brainstorming`", but the product moved to the new repo `rodge` on 2026-11-03, so the exception should name rodge (or both).

## Goal

The exception in the Execution Discipline section names the repo where the product's planning talks now happen.

## Context

- `C:\Users\tecno\.claude\CLAUDE.md:72`: "Exception: dashboard-a planning talks use `superpowers:brainstorming`, enabled only in that repo's `.claude/settings.local.json` (Joe, 2026-10-20)."
- On 2026-11-03 the product moved from `C:\Users\tecno\Desktop\Projects\dashboard-a` (now the archive, SirBepy/dashboard-a) to `C:\Users\tecno\Desktop\Projects\rodge` (SirBepy/rodge). The repo-move chat copied `.claude/settings.local.json`, which enables the plugin, into rodge.
- The same line also lives in the Dane-profile copy of the global CLAUDE.md (`C:\Users\tecno\.claude-dane\CLAUDE.md`), if that copy is maintained separately.
- Found by the repo-move chat's audit. It did not edit the line because global edits from a project session need Joe's word.

## Approach

Change the exception to "rodge (formerly dashboard-a) planning talks ...", in every copy of the global CLAUDE.md.

## Acceptance

`grep -n "planning talks" C:\Users\tecno\.claude\CLAUDE.md` names rodge.

## Notes

- 2026-11-07: CLAUDE.md Execution Discipline exception now names rodge (was dashboard-a), no words added net.
