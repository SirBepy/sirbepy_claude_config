<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=9, reconfirm-count=2, content-hash=1d7563a4 -->
# /commit: the pre-commit hook can eat a concurrent session's work, and pathspec does not protect it

**Type:** skill-improvement
**Origin:** ai

> **Recurrence, 2026-08-05 (frontend2, no worktree).** All six commits of a session
> ran through the hook without `--no-verify`, because `/commit` never mentions it and
> the project memory that authorizes it is not consulted at commit time. Two new
> costs, neither involving a concurrent session: a 2-minute `git commit` timeout left
> a stale `.git/index.lock` that blocked the retry; and because lint-staged runs
> `eslint --fix` BEFORE `prettier --write`, prettier's re-wrapping pushed a component
> from 150 to 152 lines and introduced a real `max-lines-per-function` ERROR *after*
> eslint had already passed. The branch carried that error until the next manual
> `npm run lint`. A later subagent then reported it as "pre-existing", which it was
> not. This makes the fix below more urgent, and it should also make `/commit`
> re-run lint after a hook-mediated commit that touched a file near a budget.

## Goal

Make `/commit` tell a session when to bypass the pre-commit hook, so the next one does not discover
the failure mode by destroying somebody's uncommitted work.

## Context

`C:\Users\tecno\.claude-fibo\skills\commit\SKILL.md` step 8 already reasons carefully about a shared
`.git/index`: it mandates a pathspec commit precisely so "it is correct whether or not a concurrent
session sharing this repo's `.git/index` has its own work staged there."

That protects the INDEX. It does not protect the WORKING TREE, and on 2026-07-29 the hook damaged the
working tree instead. Sequence, in the fibo repo with a git worktree open alongside the main checkout:

1. A pathspec commit was run correctly, as the skill instructs.
2. husky's lint-staged began "Backing up original state", then "Hiding unstaged changes to partially
   staged files", which physically removes the unstaged hunks of a partially-staged file from disk.
3. It then failed on `fatal: Unable to create '.git/index.lock': File exists` (another session's git
   process held the lock, since the `.git` is shared).
4. Its "Restoring unstaged changes" step was SKIPPED because of that failure, leaving another
   session's in-flight `PageHeader` edit deleted from `PurchaseItemsPage.tsx`.
5. Recovery was possible only because lint-staged leaves the hidden hunks in
   `.git/lint-staged_unstaged.patch`, which `git apply` restored.

The skill currently has no guidance for this, and its own "Never `git reset` or unstage entries you
didn't stage - that disrupts another session's commit prep" rule shows the intent is already there.

## Approach

1. Add a short subsection to the skill (near step 8's shared-index reasoning) stating that a
   pre-commit hook which stages, stashes, or hides files is a WORKING-TREE risk that pathspec
   commits do not mitigate, and that in a repo with a shared `.git` (worktrees, or known concurrent
   sessions) the hook should be bypassed with `--no-verify` while running the project's formatter and
   linter by hand first.
2. Name the recovery path explicitly so it is not rediscovered under pressure:
   `.git/lint-staged_unstaged.patch`, applied with `git apply` (or `--recount` after hand-trimming).
3. Cross-reference the project memory `fibo-frontend-precommit-prettier-churn`, which now documents
   this incident and is Joe's standing authorization for `--no-verify` in this repo. The global "never
   skip hooks" rule should be acknowledged, with this as its scoped exception rather than a silent
   violation.
4. Consider a cheap pre-flight the skill can run before a hook-bearing commit: if
   `git rev-parse --git-common-dir` differs from `--git-dir` (a worktree) or `.git/index.lock` exists,
   prefer `--no-verify` and say why in one line.

## Acceptance

- The skill distinguishes index safety (already covered) from working-tree safety (currently not).
- A future session reads `--no-verify` as the documented default for this repo's frontend commits,
  not as a rule violation it has to justify after the fact.
- The `.git/lint-staged_unstaged.patch` recovery path is written down.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 179; renumbered to 36 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: add a subsection near `commit/SKILL.md`'s pathspec-commit step distinguishing index
  safety (already covered) from working-tree safety (not covered). In a shared-`.git` repo (a
  worktree is present or `.git/index.lock` exists), prefer `--no-verify` plus manual format and lint;
  document the `.git/lint-staged_unstaged.patch` recovery path; add the
  `git rev-parse --git-common-dir` against `--git-dir` pre-flight check. This was produced by a
  strict second-pass re-triage that specifically asked whether a defensible answer exists without
  the dev; it concluded yes. Not executed only because the session ended.
