<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=9, reconfirm-count=1, content-hash=c783a4ff -->
<!-- duplicate-checked: grepped this backlog and done/ for "Phase 0", "close", "AskUserQuestion", "full-auto" - 954 is about code-style/tauri.md's layout rule, unrelated. Nothing covers close/SKILL.md's Phase 0 ask step. -->
# /close Phase 0 asks a question that full-auto repos forbid

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/close` Phase 0 auto-resolve its unfinished-commitments fork in repos that import
`full-auto.md`, instead of opening an `AskUserQuestion` the global rules say not to open.

## Context

Hit 2026-09-05 in `C:\Users\tecno\Desktop\Projects\server_supervisor`, which imports
`~/.claude/snippets/full-auto.md` at the top of its own `CLAUDE.md`.

`~/.claude/skills/close/SKILL.md` Phase 0 says, verbatim:

> If anything is unfinished AND this `/close` was triggered interactively (the dev typed it, or
> it's a live chain the dev is watching): print a short list (what was asked, what state it's in),
> then ask via `AskUserQuestion` with exactly two options

Phase 0 has exactly two branches: interactive (ask) and non-interactive (auto-file and continue).
There is no branch for a full-auto repo, which is interactive but must not be asked. Global
`CLAUDE.md` says "Never ask mid-task", and the project memory `feedback-no-mid-task-questions`
records Joe rejecting an earlier one with "do whatever you suggest".

What happened: the visual-work check fired (two UI files changed, zero screenshots captured), the
skill's interactive branch was followed literally, and a question card was posted. Joe killed it by
interrupting the turn and replying with a fresh instruction instead of answering. The question was
also redundant on its own merits: the project memory `reference-browser-test-frontend` already
records that a browser screenshot must NOT be offered to sign off a pure-move refactor, because the
screen renders as an IPC-error shell that reads as broken, and that is exactly what the change was.

So there are two defects here, and the second is the more general one:

1. Phase 0's interactive branch has no full-auto carve-out.
2. Nothing in Phase 0 tells the reader to check existing memory for a decision that already settles
   the fork before composing the question at all.

## Approach

Add a third branch to Phase 0, between the two that exist, rather than rewording either:

- If the repo's own `CLAUDE.md` imports `~/.claude/snippets/full-auto.md`, treat the fork exactly as
  the non-interactive branch already does: pick "close anyway", file the unfinished item per Phase 3,
  and print one line naming the choice and why. Never post the card.
- Detection should be the literal import line in the project `CLAUDE.md`, not a guess about
  repo ownership, so it stays mechanical.

Separately, add one sentence to Phase 0 ahead of the ask: search this project's memory for the
subject first, and if a memory already decides the fork, apply it and log that rather than asking.
That is the half that generalises past this one skill.

Worth checking in the same pass whether `/close`'s Phase 0 is the only scripted `AskUserQuestion`
step with this problem, or whether other skills carry the same interactive-branch assumption. Do not
change any other skill in this todo without saying so; just report what you find.

## Acceptance

- A `/close` run in a repo importing `full-auto.md` with an unfinished item posts no question,
  files the item, and prints the auto-resolved choice.
- A `/close` run in a repo that does NOT import it still asks exactly as today.
- Phase 0 names the check-memory-first step before its ask.
- `python ci/run_all.py` passes.

## Notes

Filed 2026-09-05 from a `server_supervisor` session, into this repo's backlog because the fix edits
`~/.claude/skills/close/SKILL.md`. No edit to that file was made from that session, per the root
`CLAUDE.md` rule against doing global work from a project session.
