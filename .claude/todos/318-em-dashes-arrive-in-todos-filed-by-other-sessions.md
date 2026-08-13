<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Todos filed by other sessions arrive carrying em dashes, fixed by hand every time

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop em dashes entering `.claude/todos/` at write time, so whichever session next runs `/commit`
does not have to hand-edit another session's backlog file to get a clean prefilter.

## Context

Hit three times in the 2026-08-13 session alone, each time by a todo authored elsewhere and dropped
into this repo's backlog:

- `309-commit-skill-lacks-fold-into-unpushed-commit-mode.md`, 6 em dashes, hand-fixed before it
  could be archived and committed.
- `312-shortcut-done-audit-ticket-id-arg-mode.md`, 1 em dash on line 74 of the skill it produced,
  caught by the prefilter mid-commit.
- `314-flutter-e2e-login-preamble-section.md`, 2 em dashes, still uncommitted at close because it
  belongs to a live concurrent session and was left alone.

The global rule is absolute ("Never use the em dash character anywhere, ever"), and two mechanical
guards now exist, but neither covers this path:

- `skills/commit/em-dash.sh` runs at COMMIT time, so it catches the file only once someone tries to
  commit it, which is usually a different session than the one that wrote it.
- `hooks/em-dash-guard.py` is a Stop hook over assistant PROSE, so a character written into a file
  never reaches it.

The result is a recurring tax paid by whoever commits next, on content they did not write.

## Approach

The gap is a write-time check on the file itself. Options, roughly in order of how mechanical they
are:

1. A `PreToolUse` hook on Write/Edit that rejects an em dash in the content when the target path is
   under `.claude/todos/`. Exact codepoint, so essentially no false-positive surface, which is the
   same property that made `em-dash-guard.py` shippable where two heuristic spikes were rejected the
   same day. Widening it beyond `.claude/todos/` is worth considering but is a bigger call: legitimate
   em dashes exist in quoted upstream content.
2. Have the todo writers (`/create-todo`, `/close` Phase 3, `/code-check`, autopilot) run
   `em-dash.sh` on the file they just wrote. Cheap, but it is prose asking a skill to remember,
   which is exactly the shape that failed five times for the unverified-mechanism rule.

Prefer option 1. Note the exemption that matters: a todo ABOUT em dashes legitimately contains the
character as an example. `307-em-dash-stop-hook.md` did, and deleting those would have broken its own
acceptance criteria. Whatever ships must not corrupt that case, so a blanket rewrite is wrong.

## Acceptance

- Writing an em dash into a file under `.claude/todos/` fails at write time with an actionable
  message, not at commit time in a different session.
- A todo whose subject IS the em dash character can still be written, by whatever exemption the
  chosen design uses.
- Verified by actually attempting both writes, not by reading the hook.

## Notes

- Filed by `/close` Phase 1 on 2026-08-13 as a repeated manual step, third occurrence in one session.
- The three offending files above are already fixed or deliberately left to their owning session, so
  this todo is about preventing the next one, not cleaning up those.
