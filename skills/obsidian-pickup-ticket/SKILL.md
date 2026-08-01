---
name: obsidian-pickup-ticket
description: Triggers on /obsidian-pickup-ticket only. Named alias for /obsidian's "Pick up a ticket" workflow - looks up a vault ticket by ID, moves it to In Progress, hands off to the dev. Never auto-triggers on natural phrases (the dev also uses Shortcut and other trackers, so ticket-like wording must not activate this skill).
argument-hint: "<ticket-id>"
---

# /obsidian-pickup-ticket

> Same mechanism as `/handoff` -> `/create-todo`: a dedicated name pointing at `/obsidian`'s "Pick up a ticket" workflow, not a separate implementation.

Run `/obsidian`'s "Pick up a ticket" workflow (`obsidian/SKILL.md`), passing `<ticket-id>` through as the ID to resolve. Trigger on the slash command only - never on natural phrases like "tackle FSM-2" (ambiguous with Shortcut and other trackers).
