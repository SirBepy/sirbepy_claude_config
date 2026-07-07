---
name: create-todo
description: Triggers on /create-todo only. Writes a single ai_todo mid-session without waiting for /close - for a "note this for later" moment, a deferred fix, or a skill-improvement observation.
argument-hint: "<what to defer, in your own words>"
---

# /create-todo

> Write one ai_todo right now, instead of hoping /close catches it later.

## When to use

Any time something surfaces that's worth deferring but not worth stopping the current thread for:

- Joe says "note this for later" / "we should fix this eventually" / "not now, but flag it".
- Claude notices a repeated manual step, a skill that got violated or proved wrong, or a "this deserves its own skill" moment - mid-session, not just at /close time.
- An offer gets made ("want me to do X?") and declined for now but shouldn't be forgotten.

If there's no project (`.for_bepy/` has nowhere to live), say so and stop - do not create `.for_bepy/` outside a project.

## Step 1 - Determine Type

- `task` - something Claude can execute later (code, config, analysis).
- `skill-improvement` - a skill gap, a "had to do this differently than the skill said" note, or a "this project keeps needing X, maybe a local skill" observation.

Infer from context; ask only if genuinely ambiguous.

## Step 2 - Write the file

Follow `~/.claude/skills/close/ai-todos-format.md` exactly: filename (zero-padded id + kebab-case slug, scan `.for_bepy/ai_todos/` and `done/` for max id), required sections (`# title`, `**Type:**`, `## Goal`, `## Context`, `## Approach`, `## Acceptance`), and the off-limits rule (never include git instructions).

The bar is the same as /close's: a future cold AI session must be able to execute the task from the file alone. Don't write a placeholder - if there isn't enough to fill Context/Approach meaningfully yet, ask one clarifying question before writing rather than write a thin file.

## Step 3 - Confirm

Print the filename and a one-line summary. Do not run `/batch-todos` or execute the todo - this skill only files it.

## Anti-patterns

- Writing a todo for something that requires Joe's physical action (credentials, hardware, browser login) - there's no persistent home for those right now, just say it directly instead of filing a file nobody will read.
- Batching multiple unrelated asks into one file. One todo, one file, per invocation - call `/create-todo` again for a second item.
- Re-filing something that's already an open todo - skim `.for_bepy/ai_todos/*.md` titles first; if a near-duplicate exists, say so and skip writing (dedup across the whole set is `/batch-todos`'s job, not this skill's).
