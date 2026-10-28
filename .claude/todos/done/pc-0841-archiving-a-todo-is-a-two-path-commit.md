<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=6, reconfirm-count=1, content-hash=69741d6e -->
<!-- duplicate-checked -->
<!-- Grepped .claude/todos/ and done/ for two-path / git mv / complete-todo pathspec: only done/495 (the parent), no live match. -->
# ai-todos-format never says archiving a todo is a two-path commit

**Type:** skill-improvement
**Origin:** ai

## Goal

Add the pairing note todo `495` identified but could not land: `skills/close/ai-todos-format.md`
should say that archiving a todo via `complete-todo.ps1` produces a TWO-path change (the source file
deleted from `.claude/todos/`, the same file added under `done/`), so a commit pathspec that names
only one half silently drops the other.

## Context

Filed 2026-08-31 by the `/mega-todos` orchestrator, from todo `495`'s builder's out-of-scope report
(commit `ff6b7cb`).

`495` fixed the `/commit` side: step 8 now runs `git diff --cached --name-status` against the commit
pathspec and names the `git mv` two-paths rule explicitly. Its own Approach also asked for a one-line
note in `skills/close/ai-todos-format.md`, because `495`'s second reproduction (2026-08-25) was
SEVEN instances via `complete-todo.ps1` rather than a literal `git mv`, and the archival path is
where a reader of the todos contract would look.

That half was dropped on purpose: `ai-todos-format.md` was owned by a different lane in the same
`/mega-todos` batch, so letting `495`'s builder touch it would have been a concurrent-write
collision. The builder flagged it instead of widening scope.

Known, deliberate remainder, not a discovered defect.

## Approach

1. Read `done/495-commit-pathspec-drops-the-source-half-of-a-git-mv.md` and the step-8 bullet as it
   actually landed in `skills/commit/SKILL.md`, so the note points at the real gate rather than a
   remembered one.
2. Add one line to `ai-todos-format.md`'s Release / completion section: archiving is a two-path
   change, so a commit covering it must name both paths, and `/commit` step 8's staged-path check is
   what catches a half-named one.
3. Do not restate step 8's algorithm here. One pointer, so the two files cannot drift.

## Acceptance

- [ ] `ai-todos-format.md` states archiving is a two-path change
- [ ] It points at `/commit` step 8 rather than duplicating the check
- [ ] A reader arriving from the archival side learns the pathspec hazard without reading `/commit`

## Notes

- Worth roughly a 6: the enforcing half already shipped in `495`, so this is discoverability, but the
  2026-08-25 incident recurred seven times before anyone noticed, and the archival path is where the
  reader actually is when it bites.
- Added the two-path note to skills/close/ai-todos-format.md (1b8407b), pointing at /commit Staged-pathspec coverage check by NAME rather than line number, since two other agents were editing skills/commit/SKILL.md in a parallel lane at the time.
