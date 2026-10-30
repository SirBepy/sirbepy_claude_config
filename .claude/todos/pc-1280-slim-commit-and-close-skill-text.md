<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: audit bundle 3; pc-1245/pc-1247 are own-range tooling, pc-1266 is close --light steps -->
# Slim /commit and /close: move rare modes to sidecars and strip incident history from the hot path

**Type:** skill-improvement
**Origin:** dev
**Summary:** Every commit and every session close loads far less text, with the same behavior.

## Why

Joe accepted this bundle from the 2026-10-30 `/global-claude-folder-audit` run. `/commit` runs in ~569 sessions and `/close` in ~589 (2026-08-26..10-30 transcripts), so every word is read hundreds of times.

## Goal

`skills/commit/SKILL.md` and `skills/close/SKILL.md` keep only what an agent needs to act correctly on the common path; rare modes and rationale move to files read on demand.

## Context

- `skills/commit/SKILL.md` is 8,634 words; step 8 alone is 2,960 (lines ~65-102). A plain `/commit` also loads the Push pipeline (~1,800 words) and `/commit fold` (~800). There are 39 inline "todo NNN" citations with dated incidents; stripping only those saves ~900 words. The overlap-ask policy (step 8 branches 3-4) lives only in SKILL.md and must stay. Step 8 presents the by-hand chain as the procedure and `commit-pathspec.sh` as an afterthought, and never mentions `--own`/`--own-since`/`--own-range` use the way sessions actually need it.
- Moving the push list affects `skills/release/test_pipeline_order.py` and `ci/check_removed_names.py` (path updates).
- `skills/commit/SKILL.md:46` says "all 83 skills"; there are 105. The session-marker preamble (`SKILL.md:15-23`) is unnecessary on the `commit-pathspec.sh` route.
- `skills/close/SKILL.md` is 4,347 words, ~1,000 of them incident rationale and screenshot-flag machinery. Its "Manual only" wording conflicts with `CLAUDE.md:62` ("run /close yourself"). Phase 2's "<50 added lines" uses `git diff --shortstat`, which is 0 after commit. Phase 2 trusts `list_peers` = 0 while Phase 3 calls it a weak signal.

## Approach

1. `/commit`: core SKILL.md (steps 1-8 using `commit-pathspec.sh` as THE procedure), `push.md` (Push pipeline + gates), `fold.md`, `by-hand.md` (the manual step 8 fallback). One pointer line each in SKILL.md. Move incident history to commit messages / `refs/incidents.md`.
2. `/close`: same treatment; fix the three logic issues above.
3. Run `/rate-it` on the slimmed text against the old one before committing (behavior must not change).

## Acceptance

- `skills/commit/SKILL.md` core under ~3,500 words; `skills/close/SKILL.md` under ~3,000.
- `python ci/run_all.py` passes (pipeline-order test updated).
- A fresh session committing and closing in a scratch repo follows the slim versions without missing a step.
