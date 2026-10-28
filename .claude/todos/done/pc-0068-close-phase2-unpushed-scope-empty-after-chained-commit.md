<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=7, reconfirm-count=1, content-hash=f1f4c35e -->
# /close Phase 2's "unpushed" scope resolves empty when /commit already pushed earlier in the same chain

**Type:** skill-improvement
**Origin:** ai

## Goal

Fix `close/SKILL.md` Phase 2's scope-arg logic so the code-health review still has something to
check when `/commit pushnbump` (or `push`/`pushbump`) ran as a *separate* invocation earlier in
the same turn/session, before `/close` (with no further chain) was invoked on its own.

## Context

Observed 2026-08-09 in `windows_taskbar_widgets`: the dev ran `/commit pushnbump` directly (not
chained via `/close /commit pushnbump`), which committed and pushed cleanly. Immediately after,
the dev ran `/commit pushnbump and then /close`, which - having nothing left to commit - proceeded
straight into `/close`. Phase 2 says: "Determine scope arg: if commits were made this session,
pass `unpushed`; otherwise pass `uncommitted`." Commits *were* made this session, so `unpushed`
was passed to `/code-check` - but `git log @{u}..HEAD` was empty (everything already pushed),
so `/code-check` found zero files in scope and the review never actually ran against the
session's own new code (`src/widgets/conductor.ts` and friends, ~150 new lines).

The binary "unpushed vs uncommitted" check doesn't account for "committed AND pushed earlier this
session" - a third state the current logic silently treats as "nothing to review."

## Approach

`close/SKILL.md` Phase 2 needs a scope that means "everything changed THIS SESSION" rather than
"everything ahead of upstream right now" - e.g. diff against a session-start marker (first commit
sha touched this session, or session start time) rather than `@{u}`. Read `close/SKILL.md` Phase 2
and `code-check/SKILL.md`'s scope-resolution table before changing either; the fix likely needs a
new scope-arg value code-check understands (e.g. `session`) rather than overloading `unpushed`.

## Acceptance

- Running `/commit pushnbump` standalone, then `/close` with no chain, still runs a real Phase 2
  review against that session's own diff (not an empty scope).
- Existing `uncommitted`/`unpushed` behavior for the already-covered cases doesn't regress.

## Notes

Origin is `ai`: surfaced by Claude noticing the review found nothing to check in a session that
plainly had ~150 new lines of code, not something the dev flagged directly.
- Duplicate of 271 - merged during /cleanup-todos 2026-08-12. Unique repro (standalone /commit pushnbump then a bare /close resolving to an empty scope) folded into 271 Context and Acceptance before archiving.

## Merged in (2026-08-11)

Absorbed todos 225 during /cleanup-todos. Their full text is in `done/` - read them before implementing, they carry specifics this file does not.
