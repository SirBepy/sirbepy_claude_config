---
name: obsidian
description: Triggers on /obsidian only. Works with Joe's Obsidian vault: plans projects, manages tickets, captures notes, updates journal. Reads vault CLAUDE.md first.
---

# /obsidian

> Work with Joe's Obsidian vault.

**Vault path:** `C:\Users\tecno\Documents\ObsidianVault`

## Step 1 - Read vault CLAUDE.md

Always read `C:\Users\tecno\Documents\ObsidianVault\CLAUDE.md` first. It's the source of truth for folder structure, naming, templates, tags, and git workflow. Follow it exactly.

## Step 2 - Git sync first

Before any vault change, run the git workflow from vault CLAUDE.md (fetch, pull, commit pending, then proceed). Every commit is followed by push.

## Step 3 - Ask what Joe wants

Use AskUserQuestion with these options:
- Plan or brainstorm a project
- Add a ticket
- Pick up a ticket
- Quick capture to Inbox
- Update today's journal

## Workflows

### Plan or brainstorm a project

1. Ask which project. Default guess: current working directory name.
2. If `<Project>.md` missing in vault root:
   - Create from `Templates/Project.md`.
   - Derive a ticket ID prefix from the project name initials (see vault CLAUDE.md "Ticket IDs"). Check uniqueness against all other project notes' `id:` fields. If clash, propose a variant and confirm with Joe.
   - Write `id: <PREFIX>` into the project note frontmatter.
3. If `Kanbans/<Project>.md` missing, create from `Templates/ProjectKanban.md`.
   - If Joe says "milestones", "sprints", or "versions": swap columns for `Backlog / M1 / M2 / ... / Mn`. No Done column (plugin handles card completion via checkbox).
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

Use the `/obsidian-pickup-ticket` skill. It only triggers on its slash command (because Joe also uses Shortcut and other trackers, natural phrases like "tackle FSM-2" must NOT auto-trigger anything). If Joe asks to "pick up a ticket" without an ID inside this `/obsidian` flow, ask which project, list active tickets from its Kanban, let him pick one, then hand off to `/obsidian-pickup-ticket`.

### Quick capture to Inbox

1. Create `Inbox/<short title>.md` tagged `unreviewed`.
2. Write Joe's thought verbatim.
3. Commit and push.

### Update today's journal

1. Open `Journal/<YYYY-MM-DD>.md`. Create from `Templates/Journal.md` if missing.
2. Add under `## Tasks` or `## Time Blocks` based on what Joe said.
3. If Joe mentioned time: `- Activity: expected Xmin, actual Y`.
4. Commit and push.
