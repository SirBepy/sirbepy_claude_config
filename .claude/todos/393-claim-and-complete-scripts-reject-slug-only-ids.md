<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# claim-todo.ps1 and complete-todo.ps1 reject a slug-only id the contract says is valid

**Type:** task
**Origin:** ai

## Goal

Make the two backlog helper scripts accept a todo whose filename carries no numeric prefix, or
decide such files must not exist and say so, so the contract and its implementation stop
disagreeing.

## Context

`skills/close/ai-todos-format.md` states plainly that a full filename stem may be passed as `-Id`:

> pass `-Slug <slug>` or the full filename stem as `-Id` to `claim-todo.ps1` / `complete-todo.ps1`

Both scripts reject it. Reproduced twice during the 2026-08-19 mega-todos run:

- `claim-todo.ps1 -Id "close-must-not-be-deferred-behind-background-work"` failed with
  `No active todo matching id '...' found in ...` (`skills/close/claim-todo.ps1:68`).
- `complete-todo.ps1 -Id "create-pr-preview-card-never-renders"` failed with
  `No todo file matching id '...' found in ... or ...\done` (`skills/close/complete-todo.ps1:177`).

Three backlog files had no numeric prefix at the time, so this was not hypothetical. All three had
to be locked and archived by hand, which bypasses the atomic-rename mutex entirely: that is the
exact race the claim contract exists to prevent, so this is a correctness gap and not only an
ergonomic one.

## Approach

Two halves, and the second is the real decision:

1. Resolve a non-numeric `-Id` against `<stem>.md` before giving up. Both scripts already have a
   `-Slug` code path; the gap is that a stem passed as `-Id` never reaches it.
2. Decide whether prefix-less backlog files should exist at all. The contract's own filename rule
   says a zero-padded numeric prefix IS the id, which makes such a file arguably malformed, and the
   real fix would be renaming it via `reserve-todo-id.ps1`. If that is the answer, write it into
   `ai-todos-format.md` and make both scripts fail with a message naming the rename path rather than
   a bare not-found.

Do not do both silently. Pick one and record which, because the two answers imply opposite behaviour
for the next prefix-less file someone creates.

## Acceptance

- Either a stem-as-`-Id` works in both scripts, or both fail with a message that names the fix.
- `ai-todos-format.md` and the two scripts agree; whichever is wrong is corrected.
- No backlog file needs hand-archiving to leave the backlog.
