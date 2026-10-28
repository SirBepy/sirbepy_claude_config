<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=6, reconfirm-count=1, content-hash=681d1151 -->
<!-- duplicate-checked -->
<!-- checked 242-brainstorm-widen-ask-gate-to-claude-md-parity.md (the guard's hit): it is about
     which questions /brainstorm asks up front and shares only the words pattern/write/design.
     950 is about pointing Claude at /respawn when a RESTART is needed. Neither is this
     subject, the greenfield research-to-build workflow shape. -->
# Greenfield pattern: scouts write their spec packs to docs/research, and the design session respawns into the build session

**Type:** skill-improvement
**Origin:** ai

## Goal

Make two things that worked well on 2026-09-05 (head_soccer_v_fable_oneshot, a from-scratch
Roblox game) the documented default for big greenfield asks, so the next one does not
rediscover them.

## Context

1. Three read-only scouts (web research, previous-attempt post-mortem, shared-lib inventory)
   each returned a 150-300 line spec pack into the orchestrator's context. The orchestrator then
   had to send each one a follow-up message asking it to write the same report verbatim to
   `docs/research/<name>.md` so the successor session and the builders could read it from disk.
   That round trip happened three times. The dispatch should have said up front: "write the spec
   pack to `docs/research/<name>.md` and return a 20-line summary". `refs/delegation-doctrine.md`
   "Scout before builder" describes the spec pack but not where it lives; `refs/builder-preamble.md`'s
   `READ-ONLY DISPATCH` marker implies the scout writes nothing.
2. Joe proposed, and the session adopted (decision D20 in that repo): research + design + scaffold
   in one session, then `/respawn` at the "plan committed, nothing built" boundary so the build
   runs under `/autopilot` with a fresh context and `docs/plan.md` as its only spec. Joe's words:
   "first do all the research, and then you do a /respawn to get the next guy with your same
   capabilities to actually implement everything you say". Nothing in `/autopilot`, `/brainstorm`
   (greenfield exception) or `/respawn` mentions this shape.

## Approach

- `refs/delegation-doctrine.md`, "Scout before builder": add one sentence: when the spec pack
  will outlive the session (a successor, a builder fan-out), the dispatch names an output file
  under `docs/research/` that the scout writes with the Write tool, and the `READ-ONLY DISPATCH`
  marker explicitly allows that single file (this is how the 2026-09-05 dispatches ended up
  phrased after the fact).
- `skills/brainstorm/SKILL.md`, greenfield exception: after the prior-art survey and the design
  docs, name the respawn boundary as the default for a multi-phase build ("design here, build in
  a respawned autopilot session with docs/plan.md as the spec"), citing D20 of that repo.
- `skills/respawn/SKILL.md`: a one-line note that a handoff prompt may begin with `/autopilot`
  so the successor starts in the intended mode.

## Acceptance

- The three files above carry the additions, `python ci/run_all.py` passes.
- A dry read of a fresh greenfield dispatch prompt written from the doctrine names the output
  file for the scout without the orchestrator improvising it.

## Notes

- Recorded 2026-09-11. Three gaps, each confirmed empty by grep before writing and each filled with one sentence carrying its reason rather than just the rule. delegation-doctrine gained the scout spec-pack-to-disk instruction, including the carve-out that a single named output file is allowed inside an otherwise read-only dispatch. brainstorm gained the respawn boundary at plan-commit time for a multi-phase greenfield build. respawn gained the note that a handoff prompt may open with an autopilot invocation, since nothing else carries the intended mode across. The shared reason in all three: design context is large and is discarded at the boundary, so whatever the build session needs must already be on disk.
