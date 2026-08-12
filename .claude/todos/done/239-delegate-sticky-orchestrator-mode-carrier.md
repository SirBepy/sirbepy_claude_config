<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# delegate: give sticky orchestrator mode a real carrier that survives compaction

**Type:** skill-improvement

## Goal

`skills/delegate/SKILL.md` claims its orchestrator mode is "sticky" - it "survives across
turns, across other skills invoked mid-session, and across topic changes" and "ends only
when the dev types `/delegate off`" - but this stickiness currently has no real carrier
mechanism: it relies entirely on the model remembering it activated `/delegate` earlier
in the same context window. Context compaction (or any mechanism that summarizes/drops
earlier turns) can silently lose that state with no signal to the dev that orchestrator
mode reverted. Give it a real carrier: a session marker file, or a state file re-injected
by a `UserPromptSubmit` hook.

## Context

`skills/delegate/SKILL.md` (as of 2026-08-01), "Activation" section, lines 13-22:

```
## Activation

On invocation, the session ADOPTS `~/.claude/refs/delegation-doctrine.md` for its whole
remainder. Read that file now and follow it as if it were written here: the 90/10 rule,
dispatch discipline, orchestrator hygiene, and the quality tells for distrusting a report.

Confirm activation in one line, then continue with whatever the dev was doing.

The mode is **sticky**: it survives across turns, across other skills invoked mid-session,
and across topic changes. It ends only when the dev types `/delegate off` (or the session
ends).
```

There is no file write, no state marker, nothing persisted outside the model's own
context when `/delegate` activates - "sticky" is currently an instruction to the model
about how to BEHAVE, not a mechanism that survives if the model's memory of that
instruction is compacted away. This is analogous to a known gap pattern already
documented elsewhere in this codebase: `~/.claude/refs/reference_hooks_cant_invoke_slash.md`
(per project memory) already establishes that hooks can't invoke slash commands directly,
which constrains HOW a carrier could re-activate the mode, but a `UserPromptSubmit` hook
CAN inject text/context into a turn without invoking a command - which is the mechanism
this todo should investigate first.

## Approach

1. Read `skills/delegate/SKILL.md` in full, and `~/.claude/refs/delegation-doctrine.md`
   (the file the mode "adopts") before implementing.
2. **Carrier mechanism, option A (session marker file):** on `/delegate` activation,
   write a small marker file (e.g. `.claude/.delegate-mode-active` at the project root,
   or a path under the session's own state dir if one exists - check how other
   session-scoped state is tracked elsewhere in this codebase, e.g.
   `%APPDATA%\com.sirbepy.server-supervisor\supervisor\` or the `.claims/` pattern in
   `close/ai-todos-format.md`, for a precedent on where machine-local session state
   lives). On `/delegate off`, delete it.
3. **Re-injection, option A continued:** add a `UserPromptSubmit` hook (see
   `~/.claude/hooks/` for existing hook examples and the settings.json wiring pattern
   used by e.g. `hooks/schedulewakeup-guard.py`) that checks for the marker file at the
   start of each turn and, if present, injects a short reminder into context (e.g. "note:
   /delegate orchestrator mode is active for this session - see
   ~/.claude/refs/delegation-doctrine.md") so the instruction survives even if earlier
   turns describing the activation get compacted away.
4. **Carrier mechanism, option B (if a session-id-scoped state file is more appropriate
   than a project-root marker):** investigate whether Claude Code exposes a
   session-identifier the hook can read (check existing hook scripts for how they access
   session context) to scope the marker per-session rather than per-project-directory,
   which would matter if multiple sessions can be open against the same project
   simultaneously (a real scenario per this codebase's multi-account/parallel-session
   tooling).
5. Update `/delegate off`'s deactivation step to explicitly delete/clear whatever carrier
   was chosen, so the hook stops re-injecting after deactivation.
6. Cross-check `/autopilot`'s own sidebar-badge marker mechanism (`<cc-autopilot:on>` /
   `<cc-autopilot:off>`, described in `skills/autopilot/SKILL.md` "Sidebar badge"
   section) for a precedent on how this codebase already signals session-level mode state
   to something outside the model's own context - `/delegate`'s carrier problem is
   structurally similar (persistent mode state that needs to survive/be visible beyond a
   single turn) even though the badge mechanism itself communicates to the UI, not back
   into context, so it's not a direct reuse, just a relevant precedent to check.

## Acceptance

- Activating `/delegate`, then triggering a context compaction (or simulating a
  fresh-context turn), still results in orchestrator-mode behavior in the next turn - the
  UserPromptSubmit hook re-injects the reminder even though the model's own memory of the
  activation is gone.
- `/delegate off` reliably stops the re-injection (verify the marker/state file is
  actually cleared, not just that the model stops mentioning it).
- The hook fails safe: if the marker file is unreadable/corrupted, the hook does not
  crash the turn - it should degrade to "mode not detected" rather than erroring.

## Notes

- Dropped via /cleanup-todos 2026-08-11: no live incident cited, purely a theoretical compaction risk. Confirmed by dev 2026-08-11.
