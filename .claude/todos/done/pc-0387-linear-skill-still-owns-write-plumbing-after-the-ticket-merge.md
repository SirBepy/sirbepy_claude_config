<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=EASY, worth=6, reconfirm-count=1, content-hash=49ac9891 -->
# `/linear` still owns write plumbing after the `/ticket` merge, and its file has been locked four times

**Type:** skill-improvement
**Origin:** ai

## Goal

Point `/linear`'s write half at `/ticket` and leave it owning reads only, finishing the one
acceptance item todo 351 could not land.

## Context

Todo 351 merged create/update/pickup into `/ticket` on 2026-08-18, deleting
`shortcut-create-ticket`, `shortcut-update-ticket` and `shortcut-pickup-ticket`. Its acceptance
included "no skill still carries a private copy of plumbing the shared layer provides". Every
Shortcut path landed. Linear did not, for one reason only:

**`skills/linear/SKILL.md` has carried uncommitted working-tree changes from another session for
four separate attempts now** - twice during todo 375, once during 378, once during 351. On the 351
attempt `list_peers` returned no active sessions at all, so the dirty hunks are orphaned state from
a session that has since ended, not live work. Nobody has committed them and nobody is editing
them.

`skills/ticket/linear.md` worked around it correctly: it POINTS at `skills/linear/SKILL.md` for the
`Invoke-Linear` helper and the ownership gate rather than copying them, so there is no duplication
today. What is missing is the reverse pointer - `/linear` still documents its own `issueCreate`
recipe and write rules as if it were the write entrypoint.

## Approach

1. **Resolve the orphaned diff first, and do not skip this.** `git diff skills/linear/SKILL.md` to
   see what the dead session left. Decide with the dev whether it is wanted work to commit
   separately, or stale scratch to discard. Do NOT bundle it into an unrelated commit - that is
   exactly the hazard [[377-commit-pathspec-blind-to-peer-working-tree-hunks]] describes.
2. Only once the file is clean: add a short "Writes live in `/ticket`" pointer to
   `skills/linear/SKILL.md`, keeping the `Invoke-Linear` helper and the ownership gate where they
   are, since `skills/ticket/linear.md` points at both.
3. Leave the read verbs (search, list, lookup) and `queries.md` exactly as they are. `/ticket`
   deliberately does not absorb them.

## Acceptance

- `skills/linear/SKILL.md` names `/ticket` as the write entrypoint.
- The `Invoke-Linear` helper and the ownership gate stay in one place, still resolvable from
  `skills/ticket/linear.md`'s pointers.
- The orphaned working-tree diff is either committed on its own merits or deliberately discarded,
  with the dev's say-so, never silently swept into another commit.

## Notes

- Filed 2026-08-18 while completing todo 351.
- The four-time block is the actual finding here. A file that cannot be edited across four sessions
  is a process problem, not bad luck, and the orphaned-dirty-state case has no owner today.
- Related: [[351-unify-ticket-skills-behind-one-platform-inferring-entrypoint]] in `done/`,
  [[377-commit-pathspec-blind-to-peer-working-tree-hunks]].
- 1957a37: /linear now points at /ticket as the write entrypoint. Its step-1 blocker (a four-session orphaned diff) was resolved separately this run as 88cf6f8.
