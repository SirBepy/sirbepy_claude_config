---
name: github-board
description: Triggers on /github-board (or /gb) commands. Manages project work via GitHub Issues, creating epics, breaking them into tasks, planning conversationally, and implementing with a strict planning gate. Uses GitHub MCP to read/write issues. Use this skill whenever the user types /github-board, /gb, mentions epics, project planning, ticket management, or wants to track and implement features across their projects. Also triggers when the user says "add a ticket", "plan this feature", "what's on my board", "break this down", or references GitHub Issues in a project management context.
---

# /github-board

> Manage project work via GitHub Issues. Epics break into tasks. Nothing gets built without a plan.

**Alias:** `/gb` works everywhere `/github-board` does. All examples below use the full form but either works.

Uses the GitHub MCP server to create and manage issues. GitHub Issues is the single source of truth.

## Prerequisites

- GitHub MCP server must be connected (via `claude mcp add` or `.mcp.json`)
- Current directory must be a git repo with a GitHub remote

## Repo Detection

Auto-detect the target repo from the current git remote:

1. Run `git remote get-url origin`
2. Extract `owner/repo` from the URL (handles both HTTPS and SSH formats)
3. If multiple remotes exist, prefer `origin`
4. If detection fails, ask the user once and remember for the session

## Labels

The skill uses these labels for hierarchy and status:

| Label         | Color     | Purpose                               |
| ------------- | --------- | ------------------------------------- |
| `epic`        | `#6E49CB` | Groups related work under one theme   |
| `task`        | `#1D76DB` | Individual implementable unit of work |
| `bug`         | `#D73A4A` | Something broken that needs fixing    |
| `planned`     | `#0E8A16` | Plan written, ready to implement      |
| `needs-plan`  | `#FBCA04` | Awaiting planning session             |
| `in-progress` | `#F9A825` | Currently being worked on             |
| `P0-critical` | `#B60205` | Drop everything, do this now          |
| `P1-high`     | `#D93F0B` | Do this next                          |
| `P2-medium`   | `#FBCA04` | Normal priority (default)             |
| `P3-low`      | `#C2E0C6` | Nice to have, do when free            |

On first use in a repo, check if these labels exist. Create any that are missing. Do this silently, don't ask permission for label creation.

---

## Commands

### `/github-board`

Show the current board state.

1. Fetch all open issues for the repo
2. Group by: in-progress, planned, needs-plan, epics
3. Display a compact summary:

   ```
   Board: owner/repo

   In Progress:
     #12 - Fix payment crash [task] [P0]

   Planned (ready to work):
     #14 - Add push notifications [task] [P1] (epic: #10)
     #15 - Notification preferences UI [task] [P2] (epic: #10)

   Needs Plan:
     #16 - Offline mode [epic] [P1], 0/4 tasks planned

   Epics:
     #10 - Notification system [3/5 tasks done]
     #16 - Offline mode [0/4 tasks done]
   ```

   Within each group, sort by priority (P0 first, then P1, etc.).

### `/github-board add <description>`

Add a task or bug.

1. Parse the description. If multiple lines, treat each as a separate issue.
2. For each: generate a clear title, set label `task` (or `bug` if it sounds like one) + `needs-plan` + `P2-medium` (default).
3. If the user mentions urgency ("critical", "ASAP", "blocking", "when I get to it", "low priority"), assign the appropriate priority label instead of the default.
4. Write the full description as the issue body.
5. Echo back what was created and ask: "Anything else to add?"
6. Accumulate until confirmed. When adding 3+ issues (or user says "board session" or "ticket session"), batch without pausing between them. After all added: "Added N issues. Want to plan them now or later?"
7. Search existing open issues for similar titles. If found: "Looks similar to #N, same thing or separate?"

### `/github-board epic <description>`

Create an epic and break it into tasks.

This is a conversational flow:

1. **Understand the epic.** Ask clarifying questions one at a time via AskUserQuestion with 2-4 options plus "Something else". Questions should cover: what problem this solves, who it's for, key constraints, what's out of scope, technical approach.

2. **Write the epic issue.** Create a GitHub Issue with `epic` label. The body should include:

   ```markdown
   ## Goal

   What this epic achieves.

   ## Context

   Why this matters, constraints, scope boundaries.

   ## Tasks

   _Managed as linked issues below._
   ```

3. **Break it down.** Propose 3-8 tasks based on the conversation. Present them to the user for approval. Each task becomes its own GitHub Issue with:
   - `task` + `needs-plan` labels
   - Body referencing the parent epic: `Part of #<epic-number>`
   - Clear description of what "done" looks like

4. **Update the epic body** to list all task issues with checkboxes:

   ```markdown
   ## Tasks

   - [ ] #21 - Set up push notification service
   - [ ] #22 - Build notification preferences UI
   - [ ] #23 - Add notification triggers for key events
   ```

   (GitHub auto-tracks checkbox progress this way.)

5. Ask: "Want to plan any of these now, or are we done for today?"

### `/github-board plan <ref>`

Plan a single issue. Accepts `#12`, `12`, or a search term.

1. Fetch the issue. If it already has the `planned` label, say so and ask if they want to re-plan.
2. Read the issue description and any epic context (if it references a parent epic, fetch that too).
3. Generate clarifying questions. Ask one at a time via AskUserQuestion with 2-4 options plus "Something else". Cover: approach, files likely involved, dependencies on other tasks, risks.
4. Once all questions are answered, write the plan as a comment on the issue:

   ```markdown
   ## Plan

   **Approach:** Brief description of the technical approach.

   **Steps:**

   1. Step one with enough detail for implementation
   2. Step two
   3. Step three

   **Files likely involved:**

   - `src/services/notifications.ts`
   - `src/components/NotificationBell.tsx`

   **Dependencies:** #21 must be done first.

   **Risks:** Push notification permissions on iOS can be tricky.
   ```

5. Replace `needs-plan` label with `planned`.

### `/github-board planall`

Plan all unplanned issues via a single conversational session.

1. Fetch all issues with `needs-plan` label.
2. Build a flat queue of clarifying questions across all issues, grouped by issue.
3. Walk through them one at a time. Preface each question with which issue it's about.
4. As each issue's questions are resolved, write the plan comment and update its label.
5. Report summary at end: "Planned N issues. M issues total ready to work."

### `/github-board do <ref> [--commit]`

Implement a planned issue.

Accept `#12`, `12`, or a search term. Normalize to the issue number.

1. **Gate check.** If the issue doesn't have the `planned` label, enforce the Planning Gate (see below). Do not proceed.

2. **Load context.** Fetch the issue, its plan comment, and any parent epic for broader context.

3. **Set in-progress.** Replace `planned` label with `in-progress`.

4. **Implement.** Follow the plan steps. Work through them methodically.

5. **Clean up.** Run linter if one exists, fix issues.

6. **Close the issue.** Close it on GitHub with a comment linking to the commit or noting what was done.

7. **Update epic progress.** If this task belongs to an epic, update the epic's task checklist (check off the completed item). If all tasks in the epic are done, close the epic too.

8. **Commit.** Follow the Git Commits rules below.
   - If `--commit`: auto-commit.
   - Otherwise: ask via AskUserQuestion "All done! Should I commit?" with options:
     - "Commit"
     - "Commit + close issue" (if not already closed)
     - "Don't commit yet"

### `/github-board doall [--commit]`

Execute all planned issues in sequence.

For each issue with `planned` label (sorted by priority first, P0 before P1 before P2 etc., then by issue number within the same priority):

1. Run the `/github-board do` flow.
2. If blocked (e.g., depends on another issue that isn't done), stop and report: "Blocked on #N, <reason>."
3. If `--commit`: auto-commit per issue. Otherwise ask once at the end.

---

## Planning Gate

Non-negotiable. If Joe asks to implement anything tied to a GitHub Issue that doesn't have the `planned` label, whether through `/gb do` or by casually asking to build something:

> "Hold up, #N hasn't been planned yet. Run `/gb plan N` first."

Do not start the work. Do not make exceptions. The plan is what makes AI implementation reliable.

---

## Searching Issues

When a ref doesn't look like a number (e.g., `/github-board do payment crash`), search open issues by title. If exactly one match, use it. If multiple, present options. If none, say so.

---

## Epic Lifecycle

Epics auto-close when all their linked task issues are closed. When displaying an epic, always show progress: "3/5 tasks done."

When a new task is added that belongs to an existing epic, update the epic's checklist.

---

## Git Commits

Before every commit: read `~/.claude/skills/commit/SKILL.md` and follow all its rules (linter, prefix, no AI attribution).

If not in a git repo, skip commits silently, note it once.

---

## Edge Cases

- **No GitHub MCP connected:** "I need the GitHub MCP server to manage issues. Run `claude mcp add` to connect it, or check your .mcp.json config."
- **Repo not on GitHub:** "This repo's remote doesn't point to GitHub. /github-board only works with GitHub repos."
- **Issue already closed:** Don't reopen. Suggest creating a new one if needed.
- **Duplicate detection:** When adding, search existing open issues for similar titles. If found: "This looks similar to #N, same thing or separate?"
- **No open issues:** "Board is empty! Use `/gb add` or `/gb epic` to get started."
