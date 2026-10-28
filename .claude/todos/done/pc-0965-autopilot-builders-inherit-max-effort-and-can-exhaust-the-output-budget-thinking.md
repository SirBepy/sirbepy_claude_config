<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=8, reconfirm-count=1, content-hash=00ad9ebb -->
<!-- duplicate-checked: todo 491 is about the skill-name hook firing on relayed peer text; this one is about builder effort and the output cap, a different surface -->
# Autopilot builders inherit max effort and can exhaust the 64k output budget thinking without writing a file

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop a sonnet builder from spending its entire output budget on extended thinking. The first task-1.1 dispatch of the Head Soccer build session (2026-09-05, session 706da5d5) died with `max_output_tokens` after 64000 thinking tokens and zero tool calls; the retry only succeeded after the task was split into three smaller dispatches whose prompts opened with "start writing files immediately, one file per Write call, keep each response short".

## Context

The `Agent` tool schema exposed in that session had no `effort` parameter (only description, prompt, subagent_type, model, run_in_background, isolation), so `CLAUDE.md`'s "tune `effort` freely" could not be applied and the builder ran at the orchestrator's inherited `max` effort. Evidence: the task transcript's final assistant message shows `"output_tokens": 64000, "thinking_tokens": 64000, "effort": "max"` and `stop_reason: max_tokens`. The same task at the same effort finished fine once its scope was a third of the size and the prompt told it to write first.

## Approach

- `refs/builder-preamble.md` or `refs/delegation-doctrine.md`: add a short "working style" paragraph to the canonical block: fixed decisions are already made, start writing files immediately, one file per Write call, keep each response short, and split any dispatch that would create more than roughly six files.
- `skills/autopilot/SKILL.md`: under the delegation section, note that builders inherit the session's effort and that a large scope at max effort can hit the output cap before the first tool call; the fix is scope, not a retry.
- Check whether the Agent tool now accepts an `effort` field; if it does, make `effort: "medium"` (or lower) the default for builders in the doctrine's model-tier rules.

## Acceptance

- The pasted builder block carries the working-style paragraph.
- Autopilot's SKILL.md names the failure mode and the scope-split remedy.

## Notes

- DONE 2026-09-10 via /loop-todos cycle 2, and the premise was re-checked against the live tool schema rather than the todo text: the Agent tool exposes description, isolation, model, prompt, run_in_background and subagent_type, with NO effort field. So a rule saying "pass a lower effort" was unimplementable, and the fix had to be about the knob that exists. refs/delegation-doctrine.md:12-27 gains a Builder scope caps effort, not a parameter block stating the schema fact, the remedy (split the dispatch, roughly six files, instruct write-first), and the failure signature to watch for: stop_reason max_tokens with zero tool calls and no changes on disk, which reads identically to a dead agent and must be treated as a dispatch to split rather than retry. skills/autopilot/SKILL.md carries the same paragraph tied to its existing liveness machinery. Orchestrator follow-up applied on top: global CLAUDE.md line 150 said "Tune effort freely - the cheap knob", which was simply false, so it now records that the parameter does not exist and points at scope instead. Budget after that edit: 6831 of 7000, headroom 169. python ci/run_all.py exits 0.
