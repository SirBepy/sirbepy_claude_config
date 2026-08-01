---
name: obsidian-pickup-ticket
description: Named alias for /obsidian's "Pick up a ticket" workflow - looks up a vault ticket by ID, moves it to In Progress, hands off to the dev.
disable-model-invocation: true
argument-hint: "<ticket-id>"
---

# /obsidian-pickup-ticket

> Same mechanism as `/handoff` -> `/create-todo`: a dedicated name pointing at `/obsidian`'s "Pick up a ticket" workflow, not a separate implementation.

Run `/obsidian`'s "Pick up a ticket" workflow (`obsidian/SKILL.md`), passing `<ticket-id>` through as the ID to resolve. Trigger on the slash command only - never on natural phrases like "tackle FSM-2" (ambiguous with Shortcut and other trackers).
