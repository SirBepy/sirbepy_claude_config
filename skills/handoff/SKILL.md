---
name: handoff
description: Ends the current session by writing a descriptive handoff todo and pinning it to the top of PLAN.md.
disable-model-invocation: true
argument-hint: "[optional short note on where things stand]"
---

# /handoff

> Wrap this session for a fresh chat to pick up. Same mechanism as `/create-todo`'s bare/handoff mode - this just gives it a name that actually reads as "hand this off."

Runs `ai-todos-format.md`'s Handoff mode section - same as bare `/create-todo`.

All other file rules (location, filename/id, template, git-policy self-heal) live in the same
contract file.

If there's no project (no repo root for `.claude/todos/` to live under), say so and stop.

## Steps

1. Read `ai-todos-format.md`'s "Handoff mode" section and follow it exactly - no mode detection
   needed here, this command IS handoff mode.
2. If args were passed (a short note), fold them into Notes as the dev's own parting context per
   that section's instructions - don't let them override the auto-derived Goal/Context.

## Anti-patterns

- Treating this like `/close` - no retrospective, no code-health review, no terminal close, no
  memory writes. Just the todo.
- Overwriting or editing a previous handoff todo instead of writing a new one.
- Asking clarifying questions - fill from context, like `/create-todo`'s handoff mode does.
