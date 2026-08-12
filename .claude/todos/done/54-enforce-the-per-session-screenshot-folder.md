<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Make the per-session screenshot folder structural instead of a prose rule

**Type:** skill-improvement
**Origin:** ai

## Goal

Close the gap between the global rule ("throwaway verification screenshots go in
`.for_bepy/screenshots/<claude-ancestor-pid>-<ancestor-start-ticks>/`") and what actually happens,
so `/close` can purge them instead of leaving them to accumulate forever in every project.

## Provenance

Originally filed as a Hubbub project todo
(`hubbub/.claude/todos/29-screenshots-must-land-in-the-per-session-subfolder.md`). Its
project-local half is DONE and shipped; only the global half survives, which is why it lives here
now. Relocated by an `/auto-do-todos` run on 2026-08-08.

**Already done, do not redo:** `hubbub/.claude/skills/capture/scripts/capture.cjs` now refuses to
run unless it can resolve a session folder. Given no `--out-dir` and no `--session-id` (or
`HUBBUB_CAPTURE_SESSION_ID`), it hard-errors rather than silently falling back to the screenshots
root. That fallback-to-root was the actual bug, because `/close` proves ownership by subfolder and
so can never claim a loose file. That fix is one project's script, though. Every other project
still has the gap.

## Context

The rule lives in prose in the global `CLAUDE.md` UI section, and `/close` Phase 3 step 3 can only
delete files inside `.for_bepy/screenshots/<pid>-<start-ticks>/`, never inferring ownership from
mtime.

In the 2026-08-05 Hubbub session nothing landed there. That session's id was
`34000-639215453173253472` and the folder was never created. Instead four ad-hoc folders appeared,
written by the main agent and by four different subagents: `playtest-15/`, `playtest-15/fixed/`,
`playtest-15/neutral/`, `playtest-21-22/`. `/close` correctly refused to touch any of them, so they
are permanent litter alongside 12 loose `v3-*.png` files at the folder root from an earlier session.
Re-checked 2026-08-08: still all there, still unswept.

The root cause is that nothing enforces the path. Subagents do not inherit the rule, and every
dispatch that needed screenshots invented its own destination. Telling future sessions to be more
careful will not fix it. **This is an enforcement gap, not an attention gap.**

**Fresh evidence, 2026-08-08, from the very run that filed this todo.** The orchestrator embedded
the resolved session path in most of its dispatches and simply forgot it in one, the avatar-bundle
builder. That builder duly invented its own destination and wrote three screenshots to
`.for_bepy/screenshots/todo26-avatar-check/`. The orchestrator noticed afterwards and moved them by
hand. So the failure reproduced, in a session whose author had just read the rule, written this
todo, and was actively watching for it. That is about as clean a demonstration as it gets that a
per-dispatch human step cannot be the mechanism: the orchestrator was maximally primed and the
omission still happened on roughly one dispatch in eight.

## Approach

Pick mechanisms that do not depend on remembering.

- **Resolve the session id ONCE and expose it.** `~/.claude/skills/close/rename-session.ps1`
  already does the process-tree walk. Factor that walk into something a skill or a dispatch prompt
  can call and interpolate, rather than making every caller redo it. A subagent genuinely cannot
  derive the ancestor PID itself, so it must be handed the resolved absolute path.
- **Add the resolved path to the mandatory-embeds list** in `~/.claude/refs/delegation-doctrine.md`,
  the same way the stage-do-not-commit line is mandatory. See [[53-restate-project-memory-facts-in-dispatch-prompts]],
  which edits the same list; do both in one pass if you pick either up.
- **Have `/close` REPORT (not delete) any `.for_bepy/screenshots/` subfolder whose name does not
  match the `<pid>-<ticks>` shape**, so drift is visible on the next close instead of silent.
- Consider making the hard-error default from Hubbub's `capture.cjs` the pattern for any future
  screenshot tooling: refuse rather than fall back.

## Acceptance

- A session that takes screenshots through any path (main agent, subagent, a project capture skill)
  ends up with them under `.for_bepy/screenshots/<pid>-<start-ticks>/`.
- `/close` on that session reports a non-zero cleaned count.
- `/close` names any non-conforming folder shape it found.
- No new folder shapes appear under `.for_bepy/screenshots/` in any project.

## Notes

The one thing that is NOT global and does not belong here: whether Hubbub's existing litter
(`playtest-15/`, `playtest-21-22/`, the loose root scripts and 12 `v3-*.png` files) should be swept
once by hand. `/close` will never touch them under the current ownership rule. That is the owner's
call on his own project and was surfaced to him directly rather than filed; nothing was deleted.

- Re-verified 2026-08-08: partially already done, and it predates the todo. Item 2 of its Approach,
  adding the resolved `.for_bepy/screenshots/<ancestor-pid>-<ancestor-start-ticks>/` path to the
  mandatory builder-prompt embeds, already exists in `refs/delegation-doctrine.md` (in the embeds list
  and in the canonical builder preamble), landed in commit `862b02e` which predates this todo's own
  filing. Still open: no reusable session-id-resolver factored out of `close/rename-session.ps1` for
  subagents to call, and `close/SKILL.md`'s screenshot-cleanup step only reports loose root-level
  files as legacy, not non-conforming subfolder names like `playtest-15/`, which is the todo's core
  ask.
- Duplicate of 60 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
