---
name: log-conductor-todo
description: Files one todo into the Claude Conductor repo's backlog from any session; bare call files what was just discussed.
disable-model-invocation: true
argument-hint: "[what to file - empty = the Conductor issue just discussed]"
---

# /log-conductor-todo

> `/create-todo` with the target repo pinned to Claude Conductor. Use it from any session when
> something about the Conductor app itself (a bug, a missing feature, an MCP tool quirk) should
> land in that app's backlog instead of the current repo's.

Target repo, always: `C:\Users\tecno\Desktop\Projects\claude_usage_in_taskbar` (origin
`SirBepy/claude_conductor`; the folder name predates the rename). If that path is missing or its
`origin` no longer points at `claude_conductor`, say so and stop - never fall back to the current
repo.

## Steps

1. Read `~/.claude/skills/create-todo/SKILL.md` and follow it, with these overrides:
   - **Step 0 is decided:** the target is the Conductor repo above. Skip the ambiguity question.
     When the current session already runs inside that repo, it is a same-repo filing (Step 3 /
     Step 4); otherwise run its "Cross-repo filing" section against that root.
   - **Step 1 is decided: always deferral mode, never handoff.** Handing a non-Conductor
     session off into Conductor's backlog and pinning it to that repo's PLAN.md is never the
     intent here.
   - **Bare call (no args):** file the most recent Conductor-app issue raised in this
     conversation. If nothing in context is about Conductor, ask one question via
     AskUserQuestion with the 2-3 likeliest candidates rather than write a thin file.
2. Everything else (Type, `**Origin:** dev`, template, duplicate guard, id reservation, exclude
   self-heal, confirm wording) is `/create-todo`'s, unchanged.

## Anti-patterns

- Filing a finding whose fix lives in `~/.claude` (a skill, hook, global rule) here just because
  it surfaced in a Conductor chat. That belongs in `~/.claude`'s backlog via `/create-todo`.
- Executing the todo or switching working context to the Conductor repo - filing is the whole job.
