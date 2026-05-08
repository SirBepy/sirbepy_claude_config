# ai_todos/ file format

Per-task markdown files in `.for_bepy/ai_todos/` at project root. Each file is briefed densely enough that a future cold AI session can execute the task without rebuilding context.

## Filename

Zero-padded numeric prefix + kebab-case slug. Example: `03-tighten-onboarding-step-redirect.md`.

The prefix is the task's stable id. Joe references tasks by id ("do todo 03").

**Picking the next id:** scan existing filenames in `ai_todos/` (and `ai_todos/done/` if it exists), take the max numeric prefix, add 1. Never reuse ids, even after a task is deleted.

**Done tasks:** delete the file (or move to `ai_todos/done/` if Joe wants history). The id stays burned either way.

## Required sections

```md
# <one-line task title>

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

## Triggering execution

Claude does NOT auto-act on this folder. Joe triggers execution by saying "do the AI todos" or naming a specific id.
