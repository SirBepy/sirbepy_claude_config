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
2. If `<Project>.md` missing in vault root, create from `Templates/Project.md`.
3. If `Kanbans/<Project>.md` missing, create from `Templates/ProjectKanban.md`.
4. Discuss goals, blockers, priorities. Ask questions via AskUserQuestion.
5. Turn conclusions into Kanban cards or `Tasks/<Title>.md` notes from `Templates/Task.md`. Link with wiki links.
6. Commit and push.

### Add a ticket

1. Ask which Kanban plus title and context.
2. Add card to `Kanbans/<Project>.md` under Backlog by default.
3. If ticket needs detail, create `Tasks/<Title>.md` from `Templates/Task.md` and wiki-link it.
4. Commit and push.

### Pick up a ticket

1. Ask which project.
2. Read `Kanbans/<Project>.md`, list active tickets (Backlog, Ready, etc).
3. Let Joe pick one.
4. Move card to "In Progress" column.
5. If linked `Tasks/<Title>.md` exists, read and summarize.
6. Commit and push.

### Quick capture to Inbox

1. Create `Inbox/<short title>.md` tagged `unreviewed`.
2. Write Joe's thought verbatim.
3. Commit and push.

### Update today's journal

1. Open `Journal/<YYYY-MM-DD>.md`. Create from `Templates/Journal.md` if missing.
2. Add under `## Tasks` or `## Time Blocks` based on what Joe said.
3. If Joe mentioned time: `- Activity: expected Xmin, actual Y`.
4. Commit and push.
