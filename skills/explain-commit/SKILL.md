---
name: explain-commit
description: Triggers on /explain-commit only. Writes a structured deep-dive (TL;DR, context, old behavior, why it failed, the fix, trade-offs) of a git commit to .for_bepy/commits_explained/<id>.md. Use when the dev wants to understand or document why a commit was made.
argument-hint: "[ticket|hash|empty=HEAD]"
---

# /explain-commit

> Deep-dive a git commit into a markdown writeup.

## Triggering

Triggers on `/explain-commit [arg]` only. The argument is optional:

- **empty** (`/explain-commit`): explain the most recent commit on the current branch (`HEAD`).
- **ticket id** (e.g. `/explain-commit 53412`): only valid if the project uses tickets and the convention prefixes commits with the ticket id (e.g. `53412: ...`). Find the matching commit with `git log --grep="^<ticket>"`.
- **commit hash** (e.g. `/explain-commit a730b41`): use the hash directly.

If the arg is ambiguous, prefer hash interpretation. If no commit is found, stop and tell the dev.

## Source of truth

The **commit itself** is the source of truth. A linked ticket (Shortcut, Trello, Jira, GitHub Issue, Obsidian, etc.) is optional supporting context, never required. If the project clearly uses one and the commit message references it (id in the subject, ticket URL in the body), pull that ticket for extra background. Otherwise skip.

Project-management lookups when applicable:

- Shortcut MCP if the project uses Shortcut and the commit references a Shortcut id.
- GitHub Issues via `gh` if the commit references `#<num>` and the project lives on GitHub.
- Other systems: only if there is a clear, automatic way to fetch (no guessing).

## Steps

1. Resolve the commit hash from the arg (default: `HEAD`).
2. Run `git show <hash>` to read the message and full diff.
3. For each touched file: read the current state and the parent state via `git show <hash>^:<path>` to understand what changed in context.
4. If the commit references an external ticket via a recognizable pattern AND the project uses that system, fetch the ticket for extra context. Otherwise skip.
5. Pick the filename:
   - Ticket id when the commit subject starts with one (e.g. `53412: ...` -> `53412.md`).
   - Otherwise the short hash (e.g. `a730b41.md`).
6. Write `.for_bepy/commits_explained/<id>.md` using the template below. Create the folder if missing.
7. Tell the dev where the file was written.

## Template

````md
# <id>: <commit subject>

## TL;DR

One or two sentences: the user-visible bug or change, and how the fix addresses it. No jargon.

## the context

Background a reader needs to follow the commit: relevant flow, key URLs / files, how the affected mechanism works in normal operation. Only what is load-bearing.

## the old behavior (before the fix)

The exact code or pattern that existed before. Quote the relevant snippet from the parent state. Explain what it was trying to achieve.

## why it failed (the bug)

Walk through the failure step by step. Use a table when there is a sequence of state changes (e.g. URL transitions, state mutations). End with the user-visible symptom.

## the fix

Quote the new code from the diff. Explain what changed and why the change addresses the root cause, not just what it does.

## trade-offs (worth knowing)

Side effects, looseness, follow-up work. Skip the section entirely if there are genuinely no trade-offs.
````

## Style

- Match the dev's lowercase / fragment writeup style.
- No em dashes.
- Quote real code from the diff, not paraphrased pseudocode.
- Reference file paths with `file:line` format when pointing at specific lines.
- If the commit touches multiple unrelated concerns, write one section per concern (do not split into multiple files).
- For non-bug commits (refactors, features, chores), reframe sections naturally: "the old behavior" -> "the prior approach", "why it failed" -> "why it needed changing", etc. Skip sections that don't apply.

## Examples

Reference writeup: `.for_bepy/commits_explained/53412.md` in zng-app. Match that depth and structure.
