<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1249 is kickoff.py script hardening from a code-check, not draft visibility -->
# zng-kickoff misses unsent drafts and open items from earlier hub chats

**Type:** skill-improvement
**Origin:** ai

## Goal
`/zng-kickoff` step 2 finds every still-unsent draft in the project's Drafts panel and any handoff from the previous day's hub chat. A feed item that already has a reply draft waiting is reported as "post the existing draft", never drafted a second time.

## Context
- On the 2026-10-26 run, step 3 surfaced sc-56344 (Johanna's question from Oct 23) as needing a reply, and the hub drafted a new one.
- The Oct 23 hub chat had already drafted the same reply ("Johanna Chen #4"). It sat unsent in the Drafts panel.
- Joe asked "r u 100% sure we didnt already reply to that". Only a transcript grep of the Oct 23 chat found the duplicate.
- The Oct 23 hub also held an unfiled FE ticket draft for sc-56375 that today's run didn't see until the old chat posted a handoff message on the channel.
- Root cause: step 2 says "Open drafts from the injected drafts list", but Conductor injects only drafts written in THIS chat. Drafts from the project's other chats are left out on purpose, so step 2 can never see them.

## Approach
In `skills/zng-kickoff/SKILL.md` step 2 (and `scripts/kickoff.py leftovers`, if it can read the drafts store), list the project's open drafts across all chats from the drafts store on disk (`src-tauri/src/sessions/message_drafts/` in claude_usage_in_taskbar shows where they persist). In step 3, check each feed ticket against those drafts by ticket id in the draft topic, and report "draft already exists" instead of drafting again.

## Acceptance
A kickoff run where an earlier chat left an unsent `sc-<id> ...` Shortcut draft reports that draft under Leftovers, and its step 3 does not write a new draft for the same ticket.
