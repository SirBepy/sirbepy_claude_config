---
name: rate-it-and-commit
description: Rates a change with /rate-it, then commits if it scores at or above threshold. Below threshold, offers iterate-first or commit-anyway. Default threshold 8. Model-invocable on purpose, so a plain "rate this and commit it if it's good" can fire it.
argument-hint: "[file-or-description] [--threshold=N]"
---

# /rate-it-and-commit

> Rate a change. If it's good enough, commit it. If not, decide what to do.

## Argument parsing

```
/rate-it-and-commit [target] [--threshold=N]
```

- `target` — optional. A file path (e.g. `skills/clockify-reconciliator/SKILL.md`) or a plain description (e.g. "the clockify rule"). If omitted, falls back to full diff.
- `--threshold=N` — score required to auto-proceed to commit. Default: 8.

## Input resolution

Determine what to review before rating:

1. **File path given:** run `git diff <file>` and use that as the review content. If the file has no diff, check `git diff HEAD <file>` (staged). If still empty, say so and stop.
2. **Description given (non-path text):** use the most recently discussed change matching that description from session context. Read the relevant file diff if needed.
3. **Nothing given:** run `git diff` (all unstaged changes). If empty, run `git diff HEAD` (staged). If still empty, say so and stop.

## Flow

1. **Rate it.** Invoke the `/rate-it` skill, passing the resolved diff content as the thing to rate. Use solo mode (no panel) unless the user explicitly passed a panel size. This is a nested invocation: `/rate-it-and-commit` owns the terminal question, and `/rate-it`'s own post-rating "Next move" menu is suppressed for it (per `/rate-it`'s nested-invocation note).
2. **Check threshold.**
   - Score >= threshold: show a one-line summary `"Score X/10 - committing."` then invoke `/commit`, telling it which paths belong in this commit as context if a target file was specified, and verifying its proposed pathspec matches before it proceeds.
   - Score < threshold: ask via AskUserQuestion (see below). Do NOT auto-commit.

## Below-threshold question

Before asking, check whether the `/rate-it` "How to raise the score:" bullets would bring the score to threshold if applied. If yes, include option 1 below; otherwise omit it.

```
Question: "Score is X/10 - below threshold of N. What now?"
Header: "Next move"
Options:
  1. "Accept suggestions, then commit" (only if lifts would reach threshold) - apply the How-to-raise bullets to the target file, then invoke /commit.
  2. "Iterate first, then commit" - invoke /iterate-it on the same target, wait for convergence, then invoke /commit.
  3. "Commit anyway" - skip iteration, invoke /commit immediately.
  4. "Abandon" - stop. Do not commit.
```

## Rules

- Never commit silently. Always show the score before committing.
- When invoking `/commit`, tell it which paths belong in this commit as context if a target file was specified, and verify its proposed pathspec matches - `/commit` does not accept a file argument, it derives its own pathspec from `git status`/`git diff`. Don't accidentally commit unrelated dirty files.
- If `/rate-it` is already running in this session (e.g. user invoked it manually before calling this skill), read the score from context rather than re-running it.
- If the user passes a panel size (integer before the target), forward it to `/rate-it`.
