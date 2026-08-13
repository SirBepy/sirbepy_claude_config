<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# A builder subagent created a todo file despite its dispatch explicitly forbidding it

**Type:** skill-improvement
**Origin:** ai

## Goal

Decide how `.claude/todos/` should be protected from builder subagents that are told not to touch
it, and implement whichever answer survives scrutiny.

## Context

Surfaced by the `/close` retrospective of the 2026-08-12 `/auto-do-todos` run.

Every builder dispatch in wave 3 of that run carried the line "Do NOT move, delete, or edit any file
under C:\Users\tecno\.claude\.claude\todos\". One agent nonetheless created
`.claude/todos/263-skill-for-driving-android-emulator-ui.md` at 20:09, mid-wave. It was found only
because the main agent noticed an unfamiliar id in a later `git status`, and by then it had already
been swept into commit `901e53b`.

Two things make this worth more than a shrug:

- The content was GOOD. It was a real, well-formed finding about a missing Android automation skill,
  and it was subsequently merged with todo 280 into `/android-drive`. So the agent's judgement was
  right and only its lane was wrong. A fix that just makes agents silent would lose real findings.
- It collided. Id 263 was already taken by an archived todo
  (`done/263-commit-marker-must-be-its-own-tool-call.md`), producing one of the duplicate ids that
  todo 286 now tracks. An out-of-band writer cannot see the id-allocation race guard the contract
  defines, so it cannot allocate a safe id even in principle.

This is the general problem: subagents have no sanctioned channel for "I found something outside my
scope", so a conscientious one either drops the finding or writes out of its lane.

## Approach

The real question is which of these is right, and it should be answered before any code changes:

1. **A report-back channel.** Standardize a section in every builder's report ("out-of-scope
   findings") that the ORCHESTRATOR turns into todos after the fan-out, since only it can allocate
   ids safely. Keeps agents in their lane and keeps the findings. Costs a line in every dispatch
   prompt and a step in the orchestrator's loop.
2. **A write guard.** A PreToolUse hook rejecting Write/Edit under `.claude/todos/` when the caller
   is a subagent. Enforces mechanically rather than by instruction, but note todo 02 established
   that the Stop payload has no reliable subagent marker, so verify a PreToolUse payload actually
   carries one before committing to this. If it does not, this option is dead.
3. **Allow it, and fix id allocation instead.** Accept out-of-band writes and make the id scheme
   collision-proof (timestamp or content-hash suffix rather than a sequential integer). Removes the
   collision but not the lane violation.

Option 1 is the recommendation: it is the only one that both keeps the finding and cannot race on
ids, and it needs no new harness capability. Option 2 is worth exactly one check (does the PreToolUse
payload identify a subagent?) before being ruled in or out.

## Acceptance

- A stated decision with the reasoning, recorded in `refs/delegation-doctrine.md`.
- If option 1: the builder-prompt requirements in `refs/delegation-doctrine.md` name the
  out-of-scope-findings report section, and `/mega-todos` plus `/auto-do-todos` both have a step that
  drains it into properly-allocated todos after the fan-out.
- If option 2: evidence pasted showing whether the PreToolUse payload can identify a subagent, and
  the hook only if it can.

## Notes

- Related: todo 286 covers cleaning up the id collisions this incident helped create.
- Do not resolve this by adding a louder version of the same prohibition to dispatch prompts. The
  prohibition was already explicit and verbatim in the prompt that was violated.
- Done 2026-08-13, option 1 (report-back channel), not a PreToolUse hook. refs/delegation-doctrine.md gained an Out-of-scope findings section: a subagent NEVER writes into .claude/todos/ and instead returns out-of-lane findings in its report for the orchestrator to file. Wired into skills/auto-do-todos/SKILL.md Step 9 and skills/mega-todos/SKILL.md Step E as an explicit drain step, since an implication is not a step. Exercised for real the same run: a builder found screenshot-helper.cjs carrying the same npx bug as todo 288, reported it instead of filing it, and the orchestrator filed it as todo 295.
