<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the guard's five hits are all different surfaces. 427 is about making the TESTING floor a Stop hook (no overlap with todo-file writes). 505 (already in done/) was the auto-mode preamble contradicting the shell-write ban, a different instruction and a different hook. 403, 350 and 423 share only the words "claude"/"hook"/"blocks". This one is skills/mega-todos/SKILL.md vs hooks/agent-todo-write-guard.py specifically. -->
# /mega-todos tells builders to record decisions in `.claude/todos/`, which a hook hard-blocks

**Type:** bug
**Origin:** ai
**Priority:** Med

## Goal

A `/mega-todos` builder that reaches a decide-or-wont-fix ending has one unblocked place to put the
decision, and the orchestrator reliably collects it.

## Context

Observed 2026-09-25, in a real `/mega-todos` run in `claude_usage_in_taskbar`.

`skills/mega-todos/SKILL.md` asks a builder to write its decision into the todo file it is working
from. Orchestrator-authored task text inherits that expectation for any todo whose ending is
decide-or-record-wont-fix, which in that run was todos 891, 912 and 937.

`hooks/agent-todo-write-guard.py` blocks the write. A lane builder reported back:

> Could not write a decision note into `.claude/todos/958-*.md` as the dispatch instructed -
> `hooks/agent-todo-write-guard.py` hard-blocks any agent edit under `.claude/todos/`, saying only
> the orchestrator allocates/edits there. Relaying the intended note here instead.

That builder recovered by putting the note in its report, which worked only because its report had a
free-text section it chose to use. Nothing in the skill tells a builder that fallback exists, so a
builder that attempts the write, gets blocked, and does not improvise loses the decision entirely.
The decision IS the artifact a decide-or-wont-fix todo produces: losing it means the next run
re-derives the same architectural call from scratch, which is the exact waste those todos exist to
prevent.

The hook is not wrong. `SKILL.md`'s own injected commit block already bans a builder from touching
`PLAN.md` or moving anything into `done/`, for the reason the hook exists: parallel agents clobbering
shared backlog state. The conflict is only that the skill draws that line at `PLAN.md`/`done/` while
the hook draws it around the whole `.claude/todos/` tree.

## Approach

Pick one, not both:

1. **Make the skill match the hook.** State in the builder brief that a builder never writes under
   `.claude/todos/` at all, and that a decision goes in a named `## Decisions made` section of its
   report, which the orchestrator writes into the todo at the barrier.
2. **Narrow the hook** to allow an append to a single existing todo file, keeping the ban on
   `PLAN.md`, on `done/`, and on creating or renaming.

Recommended: **option 1**. The orchestrator is already the only writer of `PLAN.md` and the only
caller of `archive-batch.ps1`, so routing decisions through it is consistent rather than a new
special case. Option 2 also still races: two builders assigned todos in the same lane could append
to the same file, and nothing today prevents that.

Either way, fix the orchestrator's half too: `SKILL.md`'s barrier step should drain a
`## Decisions made` section from every builder report, the way it already drains "Out-of-scope
findings".

## Acceptance

- [ ] `skills/mega-todos/SKILL.md` and `hooks/agent-todo-write-guard.py` agree on who may write
      under `.claude/todos/`; neither carries an instruction the other rejects.
- [ ] A builder reaching a decide-or-wont-fix ending has one documented, unblocked channel for the
      decision.
- [ ] `SKILL.md`'s barrier step names that channel as something the orchestrator drains, alongside
      "Out-of-scope findings".

## Notes

- `refs/builder-preamble.md`'s existing "Out-of-scope findings" section is the precedent for a
  builder handing structured non-code output back to the orchestrator, so option 1 adds a sibling to
  something that already works rather than inventing a mechanism.
