---
name: plan-todos
description: Triggers on /plan-todos only. Creates or reorders PLAN.md, the ordered lane of pointers into the todos backlog.
argument-hint: "[show | free-text ordering like 'do 07 then 03, 09 and 12 in parallel']"
---

# /plan-todos

> Order the backlog: which todos to pull next, in what sequence.

All format rules (PLAN.md schema, pointer-only lines, `[P]` markers, phases, CAS edit
discipline, pruning, git policy) live in `~/.claude/skills/close/ai-todos-format.md` - follow
that contract. This skill only edits ordering; it never executes todos (that's `/pickup`) and
never creates backlog content (that's `/create-todo` and friends).

## Step 1 - Load state

Read `.claude/todos/PLAN.md` (if present) and glob the backlog (`.claude/todos/*.md`, skip
`PLAN.md` and `done/`). Prune plan lines whose todo file vanished, silently.

If the backlog is empty: say so and stop.

## Step 2 - Parse intent

Args are natural language:

- **`show` / bare invocation with an existing plan:** print the current lane - each line as
  `<id> <todo title> [P if marked]` with phase headings, plus how many backlog todos are
  unplanned. Then ask via AskUserQuestion whether to reorder, add unplanned items, or leave it.
- **Free-text ordering** ("do 07 then 03", "09 and 12 can run together", "phase 1 is the auth
  stuff"): translate to plan lines - sequence order, `[P]` for items named as parallel-safe,
  `## Phase` headings when the dev groups. Ids the dev names by topic instead of number: resolve
  against backlog titles, confirm the mapping in the summary.
- **Bare invocation with NO plan:** propose one - read backlog titles + Goals, suggest a sensible
  order (handoffs and blockers first, quick wins next, big open-ended items last), present it,
  and ask via AskUserQuestion: accept, edit (dev says what to change), or cancel.

## Step 3 - Write

Apply per the contract's CAS discipline (re-read PLAN.md immediately before writing, line-scoped
edits, create the file with a `# Plan` header if missing). Self-heal the git-policy exclude
entries. Ids referenced but missing from the backlog: warn, don't write them.

## Step 4 - Confirm

Print the resulting lane compactly (ids + titles). Mention any unplanned backlog ids left over so
the dev knows what's NOT queued.
