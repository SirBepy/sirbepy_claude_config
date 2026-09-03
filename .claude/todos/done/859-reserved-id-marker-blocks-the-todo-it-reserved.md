<!-- Claim before executing: .claude/todos/.claims/859.claim -->
<!-- duplicate-checked -->
# A reserved id marker blocks the write of the very todo it reserved

**Type:** skill-improvement
**Origin:** ai

## Goal

Reserving a todo id should not make writing that todo fail. Today the two halves of the contract
disagree, and the writer has to hand-delete a marker mid-flow.

## Context

Hit live on 2026-08-31 while running `/create-todo` in `claude_usage_in_taskbar`:

1. `~/.claude/skills/close/reserve-todo-id.ps1 -RepoRoot <repo>` reserved id 833 and wrote
   `.claude/todos/833-.reserved`.
2. Writing `.claude/todos/833-answered-question-card-resurfaces-on-every-chat-open.md` was then
   rejected by `hooks/todo-duplicate-guard.py`: *"Id 833 is already claimed by 833-.reserved. Ids
   must be unique across .claude/todos/, done/, and *-.reserved markers - run
   reserve-todo-id.ps1 ... to reserve a free one instead of picking by hand."*
3. The guard's own remedy is the command that created the collision, so following the error
   message verbatim loops.

The contract at `~/.claude/skills/close/ai-todos-format.md` already states the intended behaviour:
each marker "is deleted at the point its real todo file is written". Nothing enforces or performs
that deletion, and the guard does not exempt the writer that holds the reservation.

Cost when it fired: the deletion needed a separate shell call, that call was declined once (it
reads like an unexplained `rm` in the backlog), and the todo was left unwritten across two turns.

## Approach

Pick one, they are alternatives not steps:

1. **Guard-side exemption (smallest).** In `hooks/todo-duplicate-guard.py`, treat a write to
   `<id>-<slug>.md` as permitted when the only conflict is `<id>-.reserved`, and delete the marker
   as part of accepting the write. Keeps reservation atomic and removes the manual step entirely.
2. **Writer-side cleanup.** Have `/create-todo` and every other writer delete their own marker
   immediately before the write. Cheaper to implement, but every future writer has to remember,
   which is what already failed here.

Option 1 is preferred: the guard is the single choke point every writer already passes through.

Whichever is chosen, fix the guard's error text - pointing at `reserve-todo-id.ps1` is actively
misleading when the conflict IS a reservation.

## Acceptance

- Reserving an id and then writing that id's todo file succeeds with no manual marker deletion.
- A genuine collision (two real todo files, or a real file vs another session's live reservation)
  is still rejected.
- The guard's rejection message names the right remedy for each case.
- `ai-todos-format.md`'s "deleted at the point its real todo file is written" sentence describes
  something that actually happens.

## Notes

- Duplicate of done/851-id-guard-rejects-the-reservation-it-was-told-to-make.md, fixed 2026-09-01 by commit 32a66cd. hooks/todo-duplicate-guard.py:196 already exempts a matching <id>-.reserved marker; the deletion contract is documented at skills/close/ai-todos-format.md:71 and implemented in reserve-todo-id.ps1:46. Verified during /mega-todos 2026-09-04.
