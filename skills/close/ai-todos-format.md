# ai_todos/ file format

Per-task markdown files in `.for_bepy/ai_todos/` at project root. Each file is briefed densely enough that a future cold AI session can execute the task without rebuilding context.

## Filename

Zero-padded numeric prefix + kebab-case slug. Example: `03-tighten-onboarding-step-redirect.md`.

The prefix is the task's stable id. Joe references tasks by id ("do todo 03").

**Picking the next id:** scan existing filenames in `ai_todos/` (and `ai_todos/done/` if it exists), take the max numeric prefix, add 1. Never reuse ids, even after a task is deleted.

**Done tasks:** delete the file (or move to `ai_todos/done/` if Joe wants history). The id stays burned either way.

## Type tag

Right after the title, one line: `**Type:** task` or `**Type:** skill-improvement`.

- `task` (default, omit the line entirely on older files - absence means task) - code, config, analysis Claude can execute.
- `skill-improvement` - "this seems reusable, maybe a skill" / "had to do this differently than the skill suggested, maybe update it" / "this project keeps needing X, maybe a local skill" observations. These used to just print in /close's retrospective and get thrown away - now they persist here instead, same folder, same file format, just tagged so `/batch-todos` and a future skim can tell them apart from regular build tasks. A skill-improvement todo's Approach section names the skill file it points at.

## Required sections

```md
# <one-line task title>

**Type:** task | skill-improvement

## Goal

One or two sentences. The user-facing or code outcome we're after.

## Context

Background a future cold AI needs. Pointers to relevant writeups (e.g. `.for_bepy/commits_explained/<id>.md`), prior commits, related files with `path:line`. Why this is being deferred (so the AI knows what's already been considered).

## Approach

Concrete proposed steps. If a code shape was discussed, sketch it. Mention alternatives that were rejected and why, so the AI doesn't re-litigate.

## Acceptance

- How to know it worked.
- What must NOT regress (pointers to recent fixes, edge cases).
- Verification commands or manual repro steps if applicable.
```

Skip a section only if it genuinely doesn't apply (e.g. trivial chore with no alternatives). Never just write a title and a one-liner.

## What belongs in ai_todos

Tasks Claude can execute in a future session (code, config, skill edits, analysis) - including skill-improvement candidates, per the Type tag above.

The wrong bar: "Claude can't test it" (e.g. Playwright can't reach Tauri webview). That makes it Claude's limitation, not a reason to defer. If Joe needs to look at something first, surface it directly in the response instead of writing a file (no persistent physical-action queue right now - see CLAUDE.md's `.for_bepy Folder` section). Once he gives feedback, handle it inline in that session - don't create a new ai_todo for it.

## Triggering execution

Claude does NOT auto-act on this folder. Joe triggers execution by saying "do the AI todos" or naming a specific id.

## Off-limits content

Never include git instructions in an ai_todo (commit, push, amend, tag, etc.). Git decisions belong to Joe and the `/commit` skill. An ai_todo describes WHAT to build, not how to close the session.
