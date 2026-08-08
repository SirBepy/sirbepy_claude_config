---
name: create-todo
description: Files one todo mid-session; bare invocation = session handoff pinned to PLAN.md.
disable-model-invocation: true
argument-hint: "[what to defer - empty = hand off this session]"
---

# /create-todo

> Write one todo right now. Bare call = hand this session off to the next AI. For an explicit
> handoff, `/handoff` is the dedicated alias for this same mode - same file, same steps.

All file rules (location `.claude/todos/`, filename/id, template, git-policy self-heal) live in
`~/.claude/skills/close/ai-todos-format.md` - follow it exactly.

If there's no project (no repo root for `.claude/todos/` to live under), say so and stop.

## Step 1 - Detect mode

Parse the args as natural language, not rigid syntax:

- **Handoff mode** when: the invocation is bare, or the dev's message reads as "continue this in
  another chat" / "let's pick this up later" / frustration with the current session, or the args
  start with `next`. The deliverable is a handoff of THIS session's work. (The explicit
  `/handoff` command always runs this mode directly - no detection needed there.)
- **Deferral mode** otherwise: the args describe a discrete thing to note for later (a fix, an
  observation, an offer that was declined for now).

If genuinely ambiguous, ask once via AskUserQuestion.

## Step 2 - Determine Type

- `task` - something Claude can execute later (code, config, analysis). Handoffs are tasks.
- `skill-improvement` - a skill gap, a "did this differently than the skill said" note, or a
  "this project keeps needing X" observation. Approach names the skill file involved.

Infer from context; ask only if genuinely ambiguous.

## Step 3 - Write the file

**Deferral mode:** fill Goal/Context/Approach/Acceptance from the discussion. If there isn't
enough to fill Context/Approach meaningfully, ask one clarifying question rather than write a
thin file.

**Handoff mode:** follow the contract's "Handoff mode" section in `ai-todos-format.md` exactly -
Type, fill instructions, PLAN.md pin, and confirm wording all live there (shared with the
explicit `/handoff` command so the two never drift apart).

## Step 4 - Confirm (deferral mode)

Print the filename and a one-line summary. Do not execute the todo - this skill only files it.
Handoff mode's confirm wording is defined in the contract's "Handoff mode" section.

## Anti-patterns

- Filing a todo for something that needs the dev's physical action (credentials, hardware,
  browser login) - say it directly instead.
- Batching multiple unrelated asks into one file. One todo per invocation.
- Finalizing new todo content without a backlog-overlap check: before finalizing, grep the
  destination backlog for keywords tied to the new todo's subject (tool/component names, the
  specific question being posed) and read any hits in full. A match: fold its findings in, or
  explicitly supersede it (note the old id and why). Never leave two todos silently disagreeing.
