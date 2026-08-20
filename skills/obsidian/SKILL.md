---
name: obsidian
disable-model-invocation: true
description: "Triggers on /obsidian only. Works with the dev's Obsidian vault: plans projects, manages tickets, captures notes, updates journal, manages people. Reads vault CLAUDE.md first."
---

# /obsidian

> Work with the dev's Obsidian vault.

**Vault path:** `C:\Users\tecno\Documents\ObsidianVault`

## Step 1 - Read vault CLAUDE.md

Always read `C:\Users\tecno\Documents\ObsidianVault\CLAUDE.md` first. It's the source of truth for folder structure, naming, templates, tags, and git workflow. Follow it exactly.

## Step 2 - Git sync first

Before any vault change, run the git workflow from vault CLAUDE.md (fetch, pull, commit pending, then proceed). Every commit is followed by push.

## Step 3 - Figure out what the dev wants

Parse the text typed after `/obsidian` first. Map it to a workflow if it clearly names one with
enough detail to act on (project, title, person name, etc.):
- Plan or brainstorm a project - "plan X", "brainstorm X", project name + planning language
- Add a ticket - "add a ticket to X: title", "new ticket for X"
- Pick up a ticket - only via `/obsidian-pickup-ticket <ID>`, see that workflow's trigger note
- Quick capture to Inbox - "note this down", "remember this", a stray thought
- Update today's journal - "log today", time spent, journal-shaped text
- Manage a person - names a person plus an action ("add a gift idea for X", "update X's birthday",
  "new person: X")

If one workflow clearly matches, skip straight into it - no menu.

Otherwise (bare `/obsidian` with no further text, or text that doesn't clearly map to one
workflow), fall back to AskUserQuestion with these options:
- Plan or brainstorm a project
- Add a ticket
- Pick up a ticket
- Quick capture to Inbox
- Update today's journal
- Manage a person

## Workflows

### Plan or brainstorm a project

1. Ask which project. Default guess: current working directory name.
2. If `<Project>.md` missing in vault root:
   - Create from `Templates/Project.md`.
   - Derive a ticket ID prefix from the project name initials (see vault CLAUDE.md "Ticket IDs"). Check uniqueness against all other project notes' `id:` fields. If clash, propose a variant and confirm with the dev.
   - Write `id: <PREFIX>` into the project note frontmatter.
3. If `Kanbans/<Project>.md` missing, create from `Templates/ProjectKanban.md`.
   - If the dev says "milestones", "sprints", or "versions": swap columns for `Backlog / M1 / M2 / ... / Mn`. No Done column (plugin handles card completion via checkbox).
   - Propose `n` based on task count, target ~5 tasks per milestone, range 3-12. Group tasks semantically (related work clusters together), not chronologically-random.
4. Discuss goals, blockers, priorities. Ask questions via AskUserQuestion.
5. Turn conclusions into Kanban cards or `Tasks/<PREFIX>-<N> <Title>.md` notes from `Templates/Task.md` (see Add a ticket for ID assignment). Link with wiki links.
6. Commit and push.

### Add a ticket

1. Ask which Kanban plus title and context.
2. Read the project note's `id:` field to get the prefix.
3. Glob `Tasks/<PREFIX>-*.md`, find max N, use `N+1`.
4. Create `Tasks/<PREFIX>-<N+1> <Title>.md` from `Templates/Task.md`. Include `id: <PREFIX>-<N+1>` in the frontmatter.
5. Add `- [ ] [[<PREFIX>-<N+1> <Title>]]` to `Kanbans/<Project>.md` under Backlog by default.
6. Commit and push.

### Pick up a ticket

**Trigger:** direct invocation is `/obsidian-pickup-ticket <ID>` only - natural phrases like "tackle FSM-2" or "pick up CUT-3" must NOT auto-trigger this (the dev also uses Shortcut and other trackers, and ticket-like wording is ambiguous). If the dev asks to "pick up a ticket" without an ID inside this `/obsidian` flow, ask which project, list active tickets from its Kanban, and let him pick one.

1. **Resolve the ticket file.** Glob `Tasks/<ID>*.md` inside the vault. If no match, tell the dev the ID doesn't exist and stop.
2. **Gather context.** Read in this order:
   - The ticket note itself.
   - The project note (find via the ticket's `project:` frontmatter - it's a wiki link, so read `<Project>.md` from vault root).
   - The project's Kanban file at `Kanbans/<Project>.md`. Note which column the ticket is currently in and its sibling tickets.
   - Grep vault-root daily notes (`<YYYY-MM-DD>.md` at vault root, not `Journal/` - abandoned
     2026-05-03) for mentions of the ticket ID or ticket title.
3. **Summarize** in one short paragraph: what the ticket is (from its Notes section), current Kanban column and sibling tickets, and any relevant journal mentions.
4. **Move to In Progress.**
   - Remove the ticket's card line from its current Kanban column.
   - Add it under `## In Progress` in the same Kanban file.
   - Update the ticket's frontmatter: `status: "in-progress"`.
5. **Commit and push.** Use `/commit push`. Prefix: `CHORE:`. Message: `CHORE: start <ID> <short title>`.
6. **Hand off.** Ask the dev what he wants to do next via AskUserQuestion:
   - Start implementing
   - Add more notes/subtasks to the ticket
   - Plan the approach before coding
   - Something else

Out of scope: creating tickets (use "Add a ticket" above); closing tickets or moving to Done (manual); editing ticket content outside the status field (a separate action).

### Quick capture to Inbox

1. Create `Inbox/<short title>.md` tagged `unreviewed`.
2. Write the dev's thought verbatim.
3. Commit and push.

### Update today's journal

1. Open `<YYYY-MM-DD>.md` at the vault root (not `Journal/` - that folder was abandoned 2026-05-03; daily notes live at vault root now). Create from `Templates/Journal.md` if missing.
2. Add under `## Tasks` or `## Time Blocks` based on what the dev said.
3. If the dev mentioned time: `- Activity: expected Xmin, actual Y`.
4. Commit and push.

### Manage a person

**Disambiguation (both sub-flows):** match candidates by filename in `People/*.md` AND by each
file's `aliases` frontmatter. If more than one file plausibly matches, or the name could be a new
person distinct from an existing file, ask the dev to confirm - never guess silently.

**Add a person**
1. Get name, relationship, and any known details (birthday, aliases) from what the dev said, or ask.
2. Run the disambiguation check above. If no match, proceed.
3. Create `People/<Full Name>.md` from `Templates/Person.md`. Fill `name`, `aliases`, `relationship`, and `tags` (`person` plus a relationship tag from vault CLAUDE.md's Tags table). Leave `birthday`/`last_seen` blank if unknown.
4. Commit and push.

**Update a person**
1. Run the disambiguation check above to resolve the target file.
2. Re-read the resolved file immediately before writing - the vault is shared across concurrent sessions and nothing locks it, so edit the content as it is right now, not a stale copy.
3. Apply one line-scoped edit, never a full regenerate:
   - New info/interaction -> append a dated bullet under `## Notes`.
   - Gift idea -> append inside the `## Gift Ideas` block.
   - Changed fact (birthday, relationship, last_seen) -> edit that one frontmatter field.
4. Commit and push.
