<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=7, reconfirm-count=1, content-hash=04f27b75 -->
<!-- duplicate-checked -->
# Nothing stops a subagent running git stash on a shared tree

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the builder preamble's `git stash` ban enforceable instead of advisory. Today it is a sentence
a subagent can read and then ignore, and when it is ignored the blast radius is other agents'
uncommitted work.

## Context

Happened 2026-09-11 in `countoff`, during a `/loop-todos` run with three builders live in one
shared checkout.

The dispatch for todo 45 carried the canonical preamble verbatim, including:

> Never run `git stash`, `git reset`, or `git checkout` on paths you don't own - other agents'
> uncommitted work shares this tree.

The builder ran `git stash push -u` anyway, to take a "before" baseline for a refactor, then popped
it. Its own report said so plainly: "confirmed via a temporary `git stash push -u` / `pop`
round-trip so the 'before' numbers are real HEAD runs, not assumed."

At that moment the same tree held uncommitted work from two other builders (a `SongTrack`
extraction and an interval-overlap refactor) plus the orchestrator's own edits. The stash swept all
of it; the pop put it back. **Nothing was lost** - verified afterwards: no orphaned stash entry,
every prior commit intact, both peers' files still present and correct. But that was luck. A pop
conflict, a crash between push and pop, or a peer writing during the window would each have lost
work that was never committed anywhere.

The orchestrator only noticed because the builder's files vanished from `git status` mid-flight and
it went looking.

## Why it matters

`hooks/dispatch-preamble-guard.py` already enforces that the preamble is PRESENT - it string-checks
three markers before a dispatch is allowed. So the system guarantees the subagent is *told* not to
stash, and guarantees nothing about whether it does. That gap is invisible until it costs something,
and the cost is other agents' uncommitted work, which is the one thing in the tree with no backup.

The builder's intent was reasonable, which is what makes this worth mechanising rather than
re-wording: it wanted a genuine pre-edit baseline, the preamble offers `git worktree add` for
exactly that, and it reached for the familiar command instead. A stricter sentence would not have
changed that.

## Approach

A `PreToolUse` hook on `Bash` is the obvious shape, matching `git stash`, `git reset`, and
`git checkout --` when the invoking agent is a subagent. Things to decide, not assume:

- **Can a hook tell it is running inside a subagent?** If not, this cannot be scoped that way and
  the whole approach needs rethinking - check before building. A blanket ban would break the
  orchestrator's own legitimate uses and `/commit fold`'s deliberate, surfaced `reset --soft`.
- **`git checkout` is overloaded.** `git checkout <branch>` is not the dangerous form;
  `git checkout -- <path>` is. Match the path form, not the word.
- **`/commit fold` must keep working.** Its `reset --soft` is run only against a sha the dev named
  explicitly, and `snippets/auto-commit.md`'s Case A `update-ref` fold is a deliberate exception.
  Neither is a subagent action, so scoping to subagents may resolve this for free.
- **Say what to do instead.** A refusal that names `git worktree add` plus
  `close/safe-remove-worktree.ps1`, and points at "take the baseline FIRST, before you edit
  anything", turns a block into a correction. The preamble already carries both; the hook message
  should quote them rather than just saying no.

Worth checking first whether this is better solved by making the preamble's baseline advice louder
and earlier rather than by a hook - the builder did read the ban and did have a legitimate need, so
a hook that fires after the intent has formed is later in the chain than ideal.

## Acceptance

- A subagent running `git stash push` in a repo is refused, and the refusal names the worktree
  alternative.
- The orchestrator's own `git stash` (if it ever needs one) and `/commit fold`'s `reset --soft` are
  both unaffected. Prove each with a real invocation, not by reading the matcher.
- `git checkout <branch>` still works; `git checkout -- <path>` is refused in a subagent.
- A hook self-test under `hooks/test_*.py` covers all four cases above, so `python ci/run_all.py`
  catches a regression.

## Notes

Filed from a `countoff` session; the fix is entirely in `~/.claude/hooks/` plus possibly
`refs/builder-preamble.md`.

The preamble text itself needs no change for correctness - it already says the right thing, in the
right place, with the right alternative. This todo is about the gap between saying and enforcing,
which is the same gap `dispatch-preamble-guard.py` was built to close on the other axis.
- Completed by /loop-todos cycle 1 (2026-10-05); full CI green (7/7) before commit.
