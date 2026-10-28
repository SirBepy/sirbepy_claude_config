<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=9, reconfirm-count=2, content-hash=ff445643 -->
# /mega-todos' per-builder commit design is unsafe in a lint-staged repo, and its question cap fights the Conductor ask tool

**Type:** skill-improvement
**Origin:** ai

## Goal

Two independent changes, both surfaced by the 2026-08-11 `/mega-todos` run in the fibo repo. The
first is a data-loss hazard, the second is a throughput ceiling.

## Context

**1. Per-builder commits are dangerous when a `pre-commit` hook runs `lint-staged`.**

The skill's central mechanism is an injected commit block so each builder commits its own todo.
fibo sets `core.hooksPath` to `frontend/.husky/_`, whose `pre-commit` runs `npx lint-staged`.
`lint-staged@16` creates an internal `git stash` to hide unstaged changes before running its tasks,
then restores it. With N agents holding uncommitted work in one shared working tree, that
stash/restore cycle can swallow another agent's in-flight edits. This is not theoretical: on
2026-08-11 lint-staged fired a real backup stash on **6 of 19** commits.

The run resolved it by inverting the design after asking Joe, who chose it explicitly: builders
never touched git at all and left everything unstaged, and the main thread committed by pathspec at
each wave barrier. That worked cleanly across 19 commits with zero lost work.

The mechanic that makes barrier-commits safe is worth writing down too: `git commit -m "..." --
<pathspec>` builds a TEMPORARY index, so the hook sees only the pathspec files and never the shared
index. That is also why a pathspec commit of a file lint-staged does not match is a complete no-op
for the hook.

**2. The 8-question cap is the wrong constraint on some projects.**

`/auto-do-todos` Step 5, which `/mega-todos` adopts by reference, caps the question round at 8
questions across 2 `AskUserQuestion` calls. That cap exists because the builtin tool stops at 4
questions per call. Projects exposing `mcp__cc_conductor__ask_user_question` have no such cap, and
that tool's own description explicitly says to ask everything needed in ONE call. On a backlog whose
remaining items are nearly all pre-written decision forks, the 8-cap becomes the binding constraint
on how much a run can accomplish, for no reason. Joe answered 8 questions in a single card on
2026-08-11 without complaint.

## Approach

Files: `C:\Users\tecno\.claude\skills\mega-todos\SKILL.md` and
`C:\Users\tecno\.claude\skills\auto-do-todos\SKILL.md`.

1. Add a Step A preflight check: read `git config core.hooksPath`, and if the resulting `pre-commit`
   hook invokes `lint-staged`, switch the run to barrier-commits (builders leave changes unstaged,
   the main thread commits by pathspec at each barrier) instead of the injected per-builder commit
   block. Document the temporary-index mechanic as the reason it is safe.
2. Make the question cap conditional on which ask tool is available: keep 8 for the builtin
   `AskUserQuestion`, and lift it when `mcp__cc_conductor__ask_user_question` (or any uncapped
   equivalent) is present.

## Acceptance

- Running `/mega-todos` in a repo with a lint-staged pre-commit hook produces barrier-commits, and
  the skill text says why, without the operator having to work it out mid-run.
- The question round is not artificially truncated to 8 on a project with an uncapped ask tool.

## Notes

- completed, commit 458760a
