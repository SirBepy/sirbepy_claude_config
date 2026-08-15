<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=HARD, worth=7, reconfirm-count=1, content-hash=cc2af058 -->
# Todo id allocation is max+1, which collides whenever two sessions file at the same time

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `.claude/todos/` id allocation safe when several sessions write to the same backlog at once,
which is Joe's normal working mode rather than an edge case.

## Context

`~/.claude/skills/close/ai-todos-format.md` defines ids as the next number after the current
highest. Every writer (`/close`, `/create-todo`, `/code-check`, `/batch-todos`, autopilot) reads
the directory, picks max+1, and writes. Nothing reserves the number between the read and the write.

**Observed three times in a row on 2026-08-14**, inside a single `/close` in `~/.claude`:

1. Wrote `329-unreceipted-claims-in-chat-drafts-have-no-rule.md`. Another session had already
   written `329-playwright-mcp-screenshots-land-outside-the-session-folder.md`.
2. Renamed to `330`. `330-mockup-stage-width-lies-for-viewport-breakpoints.md` appeared.
3. Re-checked and found `331` and `332` had both been taken while the rename was in flight. Landed
   on `333`.

The rename cost two `git commit --amend` cycles and left a stale path inside the amended commit
that needed a separate `git rm --cached` to clear. `list_peers` returned no peers, because the
other writers were sessions in *other* repos filing global findings into this backlog, exactly as
CLAUDE.md's "a todo belongs in the backlog of the repo it changes" rule instructs them to.

So the collision rate is highest precisely in `~/.claude`, the one backlog every project session
writes into.

## Approach

Pick one, in preference order:

1. **Reserve before writing.** Claim the id the same way execution is claimed: create an empty
   `.claude/todos/.claims/<id>.reserve` (or an empty `<id>-*.md` placeholder) with `New-Item`, which
   fails if the path exists. On failure, increment and retry. This reuses the `.claims/` mutex the
   contract already defines and needs no id-format change.
2. **Make ids non-sequential.** A short timestamp or random suffix (`334a3f`) cannot collide, but it
   breaks every "todo 328" reference Joe types and the ordering `/plan-todos` relies on. Only pick
   this if option 1 proves unworkable.
3. **Detect and repair at read time.** Have `/cleanup-todos` renumber duplicates. This is a
   post-hoc patch, not a fix, and leaves the racing window open.

Whichever lands, `ai-todos-format.md` is the single place the rule is written and must be updated
in the same change, since every writer reads its id rule from there.

## Acceptance

- Two sessions filing a todo within the same second get two different ids, with no manual rename.
- Existing numeric references (`todo 328`) keep working.
- `ai-todos-format.md` documents the allocation procedure, not just the id format.

## Notes

- Filed by `/close` on 2026-08-14 from a first-hand triple collision, not a hypothetical.
- Related: [[328-complete-todo-does-not-check-for-a-claim]], which is the same underlying observation
  from the other end - the `.claims/` mutex exists but nothing verifies or extends it.
- The renaming work is worse than it looks: a todo whose id changes after being committed needs the
  old path explicitly removed from the commit, or the tree ends up carrying both copies.
