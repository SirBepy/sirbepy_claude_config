<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: done/pc-0337 is about deliberation before big architecture calls; this is about a mockup and assumption tests before a UI build, and not stopping at a todo -->
# /brainstorm: a UI feature goes mockup, assumption tests, then build, never stop at a filed todo

**Type:** skill-improvement
**Origin:** ai
**Summary:** The brainstorm skill shows a clickable mockup and tests risky assumptions before building, and doesn't stop at "file a todo" when the dev expects the feature built.

## Why

Joe, 2026-10-30, in a claude_usage_in_taskbar brainstorm spawned from the `~/.claude` audit session with "once the design settles, file it as a todo": after Claude filed the todo and stopped, Joe wrote "Wait what? Is design implemented or not? I want it all to be implemented at once", then "I want you to show me what it would look like and what it would feel like, and test out the things you want to test out before building it". Recorded in the vault note `Working with Claude - preferences.md`.

## Goal

`skills/brainstorm/SKILL.md` has a step for user-facing features: a clickable mockup in the preview panel plus real tests of load-bearing assumptions, before the build. A spawning session's "file it as a todo" is treated as "file it AND build it" unless the dev himself said todo-only.

## Context

- What worked in that chat: a self-contained interactive HTML mockup in the app's theme (tabs per surface, a simulated flow), checked with a headless Playwright shot before showing; nested `claude -p --output-format stream-json --verbose` runs reading the `system/init` event to test CLI behaviour; then the full build, view-spec screenshots, and one captioned preview board.
- The skill's step 5 checkpoint and the full-auto branch say nothing about a mockup or about handoffs that tell the brainstorm to stop at a todo.
- Related but distinct: `done/pc-0337` (deliberation before big architecture calls).

## Approach

1. Add a "Look and feel first" step for UI work: mockup via `show_preview` (or `/preview`), interactive where the feel matters, before the plan checkpoint.
2. Add an "Assumption tests" step: anything the design rests on that is UNVERIFIED gets a real test run before building.
3. In step 4/5, a handoff instruction from another session to "file it as a todo" does not override the dev's own intent; when unclear, file AND build.

## Acceptance

- The skill text names the mockup step and the assumption-test step, with the 2026-10-30 incident as the reason.

## Notes

- Fixed in 75f9cba.
