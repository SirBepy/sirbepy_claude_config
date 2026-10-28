<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=HARD, worth=7, reconfirm-count=1, content-hash=ec0c6c76 -->
# The content-duplicate guard is documented but nothing enforces it

**Type:** skill-improvement
**Origin:** ai

## Goal

Make it hard to write a todo that duplicates one already in the destination backlog, instead of
relying on the writer remembering to grep first.

## Context

`~/.claude/skills/close/ai-todos-format.md` has a "Content-duplicate guard" section stating that
every writer (`/create-todo`, `/handoff`, `/close` Phase 3, `/code-check`, autopilot) must grep the
destination backlog and `done/` for keywords before writing, and resolve any hit to fold-in / drop-
as-stale / drop-as-declined.

**Violated 2026-08-17 in zng-app.** A `/code-check` run wrote
`134-v2-verify-screen-adds-a-third-debit-card-form.md` covering the same file-size and extraction
finding as the already-present `130-split-v2-verify-screen.md`. Caught only by listing the backlog
directory afterwards for an unrelated reason. The duplicate was deleted and its one genuinely new
detail folded into 130.

Note the id-allocation race already has real enforcement (`reserve-todo-id.ps1`, atomic no-overwrite
rename) because it produced a repeated incident. The content-duplicate case has the same failure
profile - it is a prose rule with no mechanism, and prose rules in this tree have a track record of
being skipped (see the em-dash rule's enforcement history).

## Approach

Options, cheapest first:

1. A `PreToolUse` hook on `Write` matching `\.claude/todos/\d+-.*\.md$` that greps the destination
   backlog and `done/` for salient tokens from the new file's title (drop stopwords, keep
   identifiers and 4+ char words) and blocks with the candidate matches listed when it finds a
   plausible hit. Same shape as the existing `shortcut-create-guard.py` / `dispatch-preamble-guard.py`
   pattern. Must be advisory-with-override, not a hard block - a genuinely distinct todo can share
   vocabulary with an existing one.
2. Failing that, a helper script (`check-todo-duplicate.ps1 -RepoRoot <path> -Title "<title>"`)
   that `ai-todos-format.md` names as the required step, the way `reserve-todo-id.ps1` is named for
   ids. Weaker, since it still relies on the writer running it.

Prefer 1. The whole lesson from the id-race incident is that a step which must be remembered will
eventually be forgotten.

## Acceptance

- Writing a todo whose title closely matches an existing backlog or `done/` entry surfaces the
  match before the file is created.
- A deliberately distinct todo that happens to share a word or two still writes without friction.
- `ai-todos-format.md`'s Content-duplicate guard section points at whatever mechanism lands.

## Notes

Filed from a zng-app session per CLAUDE.md's rule that findings about the global `~/.claude` tree
belong in this repo's backlog, not the surfacing project's. Not executed there - global work needs
Joe's say-so in the session that does it.
- a38d14e: content-duplicate guard is now enforced by a PreToolUse hook on todo writes, advisory with an override path, plus its own test file.
