---
name: create-todo
description: Triggers on /create-todo only. Files one todo mid-session; bare invocation = session handoff pinned to PLAN.md.
argument-hint: "[next] [what to defer - empty = hand off this session]"
---

# /create-todo

> Write one todo right now. Bare call = hand this session off to the next AI.

All file rules (location `.claude/todos/`, filename/id, template, git-policy self-heal) live in
`~/.claude/skills/close/ai-todos-format.md` - follow it exactly.

If there's no project (no repo root for `.claude/todos/` to live under), say so and stop.

## Step 1 - Detect mode

Parse the args as natural language, not rigid syntax:

- **Handoff mode** when: the invocation is bare, or the dev's message reads as "continue this in
  another chat" / "let's pick this up later" / frustration with the current session, or the args
  start with `next`. The deliverable is a handoff of THIS session's work.
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

**Handoff mode:** the todo IS the session handoff - be VERY descriptive; length is fine when it
helps the next AI. Fill from the session itself, no questions:

- **Goal** - what the dev is ultimately trying to achieve (the original ask, not the last subtask).
- **Context** - what was tried and in what order, where it failed or stalled, what the
  misunderstandings were (places the dev corrected course, wrong assumptions made), and any
  decisions already settled so the next AI doesn't re-litigate them.
- **Approach** - the concrete next steps as best currently known.
- **Verify** - up to ~6 real commands the resuming session runs first (start with `git pull` if
  the repo has a remote; include the project's fast checks if relevant).
- **Notes** - open decisions the dev still owes answers on, plus anything that fits nowhere else.

## Step 4 - Pin handoffs to the plan (handoff mode only)

Prepend `- [ ] <id> - <short label>` to PLAN.md (create it with a `# Plan` header if missing),
per the contract's CAS edit discipline. Deferral-mode todos are NOT auto-planned - ordering the
backlog is `/plan-todos`'s job.

## Step 5 - Confirm

Print the filename and a one-line summary (plus "pinned to top of PLAN.md" for handoffs). Do not
execute the todo - this skill only files it.

## Anti-patterns

- Filing a todo for something that needs the dev's physical action (credentials, hardware,
  browser login) - say it directly instead.
- Batching multiple unrelated asks into one file. One todo per invocation.
- Re-filing an existing todo - skim `.claude/todos/*.md` titles first; if a near-duplicate
  exists, say so and skip (full dedup is `/batch-todos`'s job).
