<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: todo 82 (done) is about clockify-reconciliator's own skill logic checking feedback_clockify_* memory files before proposing entries - unrelated to this todo, which is about two separate, whole memory DIRECTORIES (.claude vs .claude-personal) existing for the same project. Only shared vocabulary ("memory", "claude", "personal"). -->
# Reconcile the two zng-app memory directories (.claude vs .claude-personal)

**Type:** task
**Origin:** ai

## Goal

Figure out whether `C:\Users\tecno\.claude\projects\c--Users-tecno-Desktop-Projects-zng-app\memory\`
is a dead legacy copy or still a live write target for some session, and if it's dead, say so
somewhere discoverable (or delete/archive it) so a future `/cleanup-memory` run doesn't find the
same split again.

## Context

Found 2026-10-10 while auditing memory for the zng-app project. The project's auto-memory context
for the active session names
`C:\Users\tecno\.claude-personal\projects\c--Users-tecno-Desktop-Projects-zng-app\memory\` as the
live directory, and that's what `/cleanup-memory` ran against (334 files, cleaned to 330).

While verifying one suggested-drop candidate (a subagent claimed `feedback_plan_mode_only_for_code`
was superseded by a global CLAUDE.md rule - it wasn't, no such rule exists, confirmed via
`grep -rn "Plan mode" C:/Users/tecno/.claude/`), that same grep surfaced a SECOND directory:
`C:\Users\tecno\.claude\projects\c--Users-tecno-Desktop-Projects-zng-app\memory\` - note `.claude`,
not `.claude-personal`. It has its own `MEMORY.md` and its own copy of (at least)
`feedback_plan_mode_only_for_code.md`. UNVERIFIED: whether this second directory is still written
to by any current session/harness path, or whether it's a stale leftover from before Auto Memory
moved to the `.claude-personal` location - nobody has checked which sessions' auto-memory context
actually points at it, or when either directory was last modified by something other than this
investigation.

## Approach

1. Compare `ls -la` / mtimes on both directories' top-level files to see which one has recent
   activity and which looks frozen.
2. Check whether any current session type (this Conductor host, a plain terminal session, a
   different harness version) still resolves its auto-memory context to the `.claude\projects\...`
   path instead of `.claude-personal\projects\...` - if some session type still writes there, it's
   not dead, and the real fix is making sure every session type converges on one location, not
   deleting anything.
3. If confirmed dead: move it under its own `archive/` (same never-delete convention
   `/cleanup-memory` uses) rather than removing it outright, and leave a short note (a `README` or
   similar) explaining why, so the next person who finds it via grep doesn't have to re-derive this.
4. If still live somewhere: figure out whether the two should be merged, and if so follow the same
   dedupe-merge discipline `/cleanup-memory`'s Step 6 uses (fold unique content into whichever
   directory wins, never silently drop either copy).

## Acceptance

- A clear, written answer (even if just this todo's own resolution notes) for "which of these two
  directories is the real one," discoverable without re-running the same grep that found this.
- No session's auto-memory writes are silently going to a directory nobody reads.

## Notes

Low urgency, pure memory-hygiene - didn't block the zng-app cleanup-memory run, which correctly
scoped itself to only the directory its own session context named. This todo exists so the split
doesn't get rediscovered from scratch next time.
- Dropped by the cleanup-todos pass 2026-10-23: premise false. The .claude-personal projects dir is a Junction to the .claude projects dir, so both memory dirs are the same directory (351 files, identical mtimes).
