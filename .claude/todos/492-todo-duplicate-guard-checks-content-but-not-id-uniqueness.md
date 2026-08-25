<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# The todo write path catches content duplicates but lets a colliding ID through silently

**Type:** skill-improvement
**Origin:** ai

## Goal

Make a duplicate numeric prefix impossible to write, the same way a content duplicate already is -
so skipping `reserve-todo-id.ps1` fails loudly instead of producing two files with the same id.

## Context

Happened 2026-08-22, in this backlog. A session filed two todos by hand-picking ids from a
`ls | tail` of the directory. That listing is ALPHABETICAL, so `479-…` sorted last among the 4xx
files while ids up to 490 already existed. Result: `481-skill-name-hook-fires-on-relayed-peer-text.md`
was written alongside the pre-existing `481-nothing-checks-a-todo-is-in-the-repo-it-changes.md`.
Two files, one id. Caught only because `mv`-ing a sibling into `done/` made the collision visible in
a later listing; nothing flagged it at write time.

`ai-todos-format.md` already has the rule, and it is emphatic - **"Picking the next id: reserve it,
don't just read it"**, pointing at `reserve-todo-id.ps1`, with its own incident history (todo 336,
three collisions in a row on 2026-08-14 from exactly the read-then-write race). So this is not a
missing rule. It is a rule with no enforcement.

The asymmetry is the tell: `hooks/todo-duplicate-guard.py` DOES fire on content overlap - it fired
on this very session, correctly, when a todo was rewritten in place. So the write path is already
hooked; it simply checks the wrong axis. A guard that stops "this looks like todo 413" but waves
through "this IS id 481" is inverted, since the id collision is the cheaper, more mechanical check
of the two.

Why it matters beyond tidiness: the id is the addressing scheme. `claim-todo.ps1` /
`complete-todo.ps1` take `-Id`, and `ai-todos-format.md` says an ambiguous id "errors naming both
candidate filenames rather than guessing" - so a duplicate id degrades every downstream tool into
requiring a disambiguator, and "do todo 481" stops meaning anything.

## Approach

1. Read `hooks/todo-duplicate-guard.py` and find where it decides to block.
2. Add an id-uniqueness check on the same hook: parse the numeric prefix of the file being written,
   scan `.claude/todos/*.md`, `done/*.md` and `*-.reserved` in the destination repo, and block on a
   match that is not the same file being edited in place. In-place rewrites must stay allowed -
   this session legitimately rewrote `684-…` and `481-…` and neither should have been blocked.
3. Make the failure message name the colliding file and tell the writer to run
   `reserve-todo-id.ps1 -RepoRoot <root>`, so the fix is one command rather than a hunt.
4. Add test cases to `hooks/test_todo_duplicate_guard.py`: new file with a free id passes; new file
   with a taken id blocks; in-place rewrite of an existing id passes; a `*-.reserved` marker counts
   as taken.

## Acceptance

- Writing a todo whose id already exists in the destination backlog (or is reserved) is blocked.
- Rewriting an existing todo in place is not blocked.
- The message names the collision and the reserve command.
- `python ci/run_all.py` exits 0.

## Notes

Cleanup owed from the incident: `481-skill-name-hook-fires-on-relayed-peer-text.md` was renamed to
`491-…` by hand once spotted, so this backlog is currently consistent. Verify that before assuming
otherwise.

Related, same root: nothing enforces the reserve step at the point of writing, only at the point of
reading the doc. Fixing the guard is the cheap half; if a stronger fix is wanted later, the writer
skills could call `reserve-todo-id.ps1` themselves rather than instructing the model to.
