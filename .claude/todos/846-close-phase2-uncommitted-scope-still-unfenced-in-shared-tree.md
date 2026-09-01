<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=1, content-hash=ac0ce4d1 -->
<!-- duplicate-checked -->
# `/close` Phase 2's `uncommitted` scope (zero-commit case) has no peer-attribution fence

**Type:** skill-improvement
**Origin:** ai

## Goal

When `/close` Phase 2 falls back to `uncommitted` scope (no commits made this session, so there's
no sha list to pass), stop it from sweeping a concurrent peer session's dirty working-tree files
into the review alongside the invoking session's own changes.

## Context

Hit 2026-08-31, `claude_usage_in_taskbar`. Session made a small, fully-scoped edit (5 files, 21
insertions) and had made zero commits by the time `/close` ran, so Phase 2's documented default is
`uncommitted` (`git diff HEAD --name-only --diff-filter=ACM`). `list_peers` confirmed two other
active sessions on the same worktree (`busy: true`). `git status --short` at close time listed 10
dirty files: the 5 this session actually touched, plus 5 more (`chat-event-handler.ts`,
`composer.css`, `tool-strip.ts`, `turn-chips.ts`, `sessions.css`) and 2 untracked files that traced
to the peers' in-flight work, not this session's task.

Todo #271 (done) fixed the analogous problem for the COMMIT-based branch: `/close` now records
this session's own commit shas and passes `shas:<list>` so `/code-check` scopes to exactly those
commits regardless of how many other sessions share the branch. That fix does nothing for the
zero-commit branch, though - `uncommitted` is a raw working-tree diff against HEAD with no
per-session attribution available at all (there's no sha to filter by; the dirty state is just
whatever's on disk right now, contributed by however many sessions are running). Todo #774 (open,
separate) covers a different bug in the same scope row - untracked files being silently dropped
entirely - not this one.

This session avoided the contamination by hand: computed `git diff --shortstat` scoped to just its
own 5 touched files (21 insertions, under Phase 2's 50-line skip gate anyway, so the review ended
up skipped regardless) rather than trusting the documented `uncommitted` default blind. That's a
workaround, not a fix - the next session that follows Phase 2 literally in a multi-peer repo will
hand `/code-check` a file list padded with someone else's unrelated code.

## Approach

- In `~/.claude/skills/close/SKILL.md` Phase 2 (and/or `code-check/SKILL.md`'s scope-resolution
  table), when falling back to plain `uncommitted` in a repo where `list_peers` shows other active
  sessions on the same worktree, don't pass `uncommitted` blind:
  - Cheapest: have the invoking session track which files IT edited this session (already
    knowable from its own Edit/Write tool calls in-context) and pass that explicit list as the
    scope arg instead - `code-check`'s scope table already accepts a bare file-path list ("Looks
    like a file path -> treat as single-file list").
  - Alternative: diff `git status --short` against a session-start snapshot of dirty files (if one
    were ever captured) to derive the delta - more mechanical but needs new state.
- Only matters when Phase 2 would otherwise proceed (own diff clears the 50-line gate) AND peers
  are present - cheap to gate on `list_peers` returning any entry before doing the extra work, so a
  solo session pays nothing extra.
- Note in the skill that `uncommitted` and `shas:` need the SAME peer-safety property; #271 only
  gave it to one of the two branches.

## Acceptance

- In a repo with an active peer session holding unrelated dirty files, `/close` Phase 2 (when it
  falls back to `uncommitted`) reviews only the invoking session's own touched files, not the
  peer's.
- A solo session (no peers) behaves exactly as today - no extra `list_peers` overhead beyond one
  cheap call already available.
- Regression case from today: 5 own files + 5-7 peer files dirty simultaneously, zero commits made
  -> resolved scope is exactly the 5 own files.

## Notes

Related but distinct from #271 (done, fixes the commit/shas branch) and #774 (open, fixes
untracked-file omission in the same `uncommitted` row) - this is the third distinct gap in that one
scope-resolution row, all discovered independently.
