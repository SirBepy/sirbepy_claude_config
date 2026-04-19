---
name: pickup-ticket
description: Look up an Obsidian vault ticket by ID, gather context, move it to In Progress, and hand off to Joe. Triggers on phrases like "tackle FSM-2", "pick up CUT-3", "work on <ID>", "start <ID>", or "/pickup-ticket". Also triggers on bare numbers ("tackle 2") when the current project is obvious from context.
---

# /pickup-ticket

> Pick up an Obsidian vault ticket and start working on it.

**Vault path:** `C:\Users\tecno\Documents\ObsidianVault`

## Step 1 - Parse the ID

- If Joe used a full ID (`FSM-2`, `CUT-3`), use it directly.
- If Joe said just a number (`tackle 2`):
  - Look at recent messages for a project reference.
  - If one project is obvious, combine its prefix with the number.
  - Otherwise ask Joe which project (AskUserQuestion with active project names).

## Step 2 - Git sync

Run the vault git workflow from `C:\Users\tecno\Documents\ObsidianVault\CLAUDE.md` before any change:
1. `git fetch`
2. `git pull` if there's anything to pull
3. Commit + push any pending uncommitted changes

## Step 3 - Resolve the ticket file

Glob `Tasks/<ID>*.md` inside the vault. If no match, tell Joe the ID doesn't exist and stop.

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

Use `/commit push`. Prefix: `FEAT:` (or `CHORE:` if not feature work). Message: `FEAT: start <ID> <short title>`.

## Step 8 - Hand off

Ask Joe what he wants to do next via AskUserQuestion:
- Start implementing
- Add more notes/subtasks to the ticket
- Plan the approach before coding
- Something else

## Out of scope

- Creating tickets -> use `/obsidian` "Add a ticket" workflow.
- Closing tickets or moving to Done -> manual or `/obsidian`.
- Editing ticket content outside the status field -> separate action.
