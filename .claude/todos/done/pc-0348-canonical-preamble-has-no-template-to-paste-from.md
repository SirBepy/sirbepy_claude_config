<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# The canonical builder preamble is "copy-verbatim" but there is nothing to copy it FROM

**Type:** skill-improvement
**Origin:** ai

## Goal

Give the canonical builder preamble a real paste source, so the block that exists specifically to
stop drift is not retyped from memory on every dispatch.

## Context

`refs/delegation-doctrine.md`'s "Canonical builder preamble" section opens by stating its own
purpose: the block is there "so it stops getting hand-retyped (and drifting) per dispatch."

But the block lives inside a fenced code block in the middle of a long prose document. To use it,
an orchestrator either re-reads that whole file per dispatch or reproduces the block from memory,
which is retyping by another name.

Measured 2026-08-15: one `/auto-do-todos` run issued 13 builder dispatches. Every preamble was
assembled by hand. Drift was visible within the single run:

- Early dispatches omitted the explicit-`timeout` line entirely, because todo 325 had not landed
  yet when they were written.
- Later dispatches carried it, so the run's own dispatches disagree with each other.
- The `~/.claude` edit-ban line was pasted into dispatches where it was actively wrong, which is
  the defect the closing code-check caught and which required commit `bdb0323` to fix.

That last one is the strongest evidence: a hand-assembled preamble propagated a rule into 5
dispatches where it contradicted the assigned task, and nothing noticed until a review pass at the
end of the run.

## Approach

Extract the block to its own file so it can be read directly, for example
`refs/builder-preamble.md`, containing only the preamble plus its placeholder table.
`refs/delegation-doctrine.md` then points at it instead of embedding it, the same way that file
already defers to `CLAUDE.md` for model tier and to `process-hygiene.md` for orphan rules.

Two details worth getting right:

- The `~/.claude` edit ban is now conditional (deleted when the session's own working directory IS
  `~/.claude`, per `bdb0323`). A template has to make a conditional line obviously conditional,
  not something a hurried reader pastes unconditionally. Consider marking it as a placeholder like
  the other four rather than as body text.
- `<ORPHAN_CHECK>` is already a placeholder precisely so a Node-running dispatch cannot lose it by
  pasting the block unread. Keep that property.

Check every consumer before moving anything: `/delegate`, `/autopilot`, `/auto-do-todos` and
`/mega-todos` all reference the doctrine, and `skills/auto-do-todos/SKILL.md:36` adopts it "in
full".

## Acceptance

- One file holds the preamble text, and the doctrine points at it rather than duplicating it.
- The conditional `~/.claude` line cannot be pasted unconditionally by accident.
- Every skill that adopts the doctrine still resolves to the same preamble content.

## Notes

- Done 2026-08-16, commit f758d2e. The canonical preamble now lives in refs/builder-preamble.md with a placeholder table; delegation-doctrine.md points at it instead of embedding it. The ~/.claude edit ban became the <GLOBAL_EDIT_BAN> placeholder so it can no longer be pasted unconditionally, which was the defect that needed bdb0323. All consumers checked: none quoted the block inline, so all still resolve to the same content.
