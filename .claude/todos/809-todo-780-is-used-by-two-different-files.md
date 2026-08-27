<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Todo id 780 is used by two different files, so claiming it by id is ambiguous

**Type:** task
**Origin:** ai

## Goal

Renumber one of the two files sharing id `780`, so an unqualified "do todo 780" resolves to exactly
one thing.

## Context

Found 2026-08-26 during an `/autopilot` backlog run. Two live backlog files claim the same id:

- `.claude/todos/780-eighteen-skills-declare-slash-only-but-are-model-invocable.md` - TRACKED,
  committed by an earlier session.
- `.claude/todos/780-guard-against-piping-cargo-test-output.md` - UNTRACKED, another session's
  uncommitted work at the time of writing.

This was the second such collision. The other, on `410`, was fixed in the same run (commit
`47f3d8a`, renumbered to `807`) because BOTH of its files were tracked and clean, so neither
belonged to a live session. `780` was deliberately left alone: renaming a file another session has
open, mid-edit, risks destroying work, and there was nobody to ask.

**Why it matters rather than being cosmetic.** `skills/close/claim-todo.ps1` and
`complete-todo.ps1` both carry a documented `-Slug` disambiguator specifically for this case, which
means the scripts do not guess, they require the caller to. A caller who passes only `-Id 780`
gets whichever file the glob returns first. That can claim one file and archive the other.

## Approach

1. Re-check first: `ls .claude/todos/780-*.md` and `git status --short -- .claude/todos/780-*.md`.
   If the untracked one has since been committed, both are tracked and this is now as safe as `410`
   was. If it is still untracked, check whether the owning session is live before touching it.
2. Renumber the file that nothing else references. Grep the whole backlog for backlinks first
   (`grep -rn "780-" .claude/todos/`): the rule used for `410` was to move the file with NO inbound
   references and leave the referenced one in place, so no `[[...]]` link breaks. Apply the same
   rule rather than picking by date.
3. Allocate the new id with `skills/close/reserve-todo-id.ps1`, then `git mv`. Delete the
   `<id>-.reserved` placeholder the script leaves behind; it is not part of the backlog.
4. Append a short note to the renumbered file recording the old id and why it moved, so a reader
   following a stale reference can find it. `807`'s Notes section is the worked example.

## Acceptance

- `ls .claude/todos/*.md | sed 's#.*/##' | sed 's/-.*//' | sort | uniq -d` prints nothing.
- Every `[[...]]` and bare-filename reference in the backlog still resolves.
- The renumbered file records its old id.

## Notes

- Same failure class as `492`, which proposes a mechanical guard against duplicate ids. `492` is
  disqualified from an unattended run because its fix writes to `hooks/todo-duplicate-guard.py`,
  where `hooks/sensitive-file-guard.py` returns `ask`. This todo is the manual cleanup; `492` is
  the prevention. Doing this one does not close that one.
- Both collisions originated the same way: a bulk filing commit allocated ids without checking the
  backlog, or two sessions reserved concurrently. `95d47fd` filed 55 todos at once and contains
  both `410` files.
