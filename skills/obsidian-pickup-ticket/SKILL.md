---
name: obsidian-pickup-ticket
description: Triggers on /obsidian-pickup-ticket only. Looks up an Obsidian vault ticket by ID, gathers context, moves it to In Progress, and hands off to the dev. Never auto-triggers on natural phrases (the dev also uses Shortcut and other trackers, so ticket-like wording must not activate this skill).
argument-hint: "<ticket-id>"
---

# /obsidian-pickup-ticket

> Pick up an Obsidian vault ticket and start working on it.

**Trigger:** `/obsidian-pickup-ticket <ID>` only. Do NOT invoke this skill from natural phrases like "tackle FSM-2" or "pick up CUT-3" - the dev uses other ticket systems (Shortcut, etc.) and those phrases are ambiguous.

**Vault path:** `C:\Users\tecno\Documents\ObsidianVault`

## Step 1 - Parse the ID

- Expected invocation: `/obsidian-pickup-ticket <ID>` (e.g. `/obsidian-pickup-ticket FSM-2`).
- If the dev passed a full ID (`FSM-2`, `CUT-3`), use it directly.
- If the dev passed just a number:
  - Look at recent messages for a project reference.
  - If one project is obvious, combine its prefix with the number.
  - Otherwise ask the dev which project (AskUserQuestion with active project names).
- If the dev passed no argument, ask which ticket (AskUserQuestion listing active tickets from his projects).

## Step 2 - Git sync

Run the vault git workflow from `C:\Users\tecno\Documents\ObsidianVault\CLAUDE.md` before any change:
1. `git fetch`
2. `git pull` if there's anything to pull
3. Commit + push any pending uncommitted changes

## Step 3 - Resolve the ticket file

Glob `Tasks/<ID>*.md` inside the vault. If no match, tell the dev the ID doesn't exist and stop.

## Step 4 - Gather context

Read in this order:
1. The ticket note itself.
2. The project note (find via the ticket's `project:` frontmatter - it's a wiki link, so read `<Project>.md` from vault root).
3. The project's Kanban file at `Kanbans/<Project>.md`. Note which column the ticket is currently in and its sibling tickets.
4. Grep `Journal/` for mentions of the ticket ID or ticket title.

## Step 5 - Summarize

One short paragraph covering:
- What the ticket is (from its Notes section).
- Current Kanban column and sibling tickets.
- Any relevant journal mentions.

## Step 6 - Move to In Progress

- Remove the ticket's card line from its current Kanban column.
- Add it under `## In Progress` in the same Kanban file.
- Update the ticket's frontmatter: `status: "in-progress"`.

## Step 7 - Commit and push

Use `/commit push`. Prefix: `CHORE:`. Message: `CHORE: start <ID> <short title>`.

## Step 8 - Hand off

Ask the dev what he wants to do next via AskUserQuestion:
- Start implementing
- Add more notes/subtasks to the ticket
- Plan the approach before coding
- Something else

## Out of scope

- Creating tickets -> use `/obsidian` "Add a ticket" workflow.
- Closing tickets or moving to Done -> manual or `/obsidian`.
- Editing ticket content outside the status field -> separate action.
