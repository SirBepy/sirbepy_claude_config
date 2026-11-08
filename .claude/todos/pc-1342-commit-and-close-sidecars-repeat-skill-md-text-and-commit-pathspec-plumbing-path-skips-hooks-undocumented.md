<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grep of backlog and done/ for by-hand.md, sidecar duplication and the plumbing commit path found nothing live; pc-1280 (the slimming itself) is the origin. -->
# /commit and /close sidecars repeat SKILL.md text, and the plumbing commit path skipping hooks is undocumented

**Type:** skill-improvement
**Origin:** ai
**Summary:** Decide the canonical copy for the text now duplicated between the /commit and /close SKILL.md files and their sidecars, and document that commit-pathspec.sh's plumbing path skips pre-commit hooks.

## Goal

Each rule lives once; a reader of `skills/commit/SKILL.md` learns that a script commit can skip hooks.

## Context

From the push-gate `/code-check` (skills/commit, close, release slice) over the range that includes commit 7de3ca0 (pc-1280 slimming):

- `skills/commit/by-hand.md:5-46` reproduces step 8 in long form while `SKILL.md` step 8 keeps a condensed copy; `by-hand.md:3` says a disagreement is a defect to fix in both. `skills/commit/edge-cases.md:89-103` repeats the step 1a bookkeeping lists it says "stay in SKILL.md step 1a", and the step 7 submodule flow exists in both `SKILL.md:50` and `edge-cases.md:95-103`.
- `skills/close/finish.md:5-38` repeats `skills/close/SKILL.md:171-197` (Phase 6) nearly verbatim: skip conditions, the HARD ORDERING RULE, the exit-3 REFUSED explanation, both rename-session lines.
- bepy-skill-creator's WARN "4+ sidecars means the skill is too broad": /commit lists 8 sidecars, /close 6.
- `skills/commit/commit-pathspec.sh` (the mode_fix branch near lines 1186-1212) routes every staged exec-bit change on a `core.fileMode=false` repo, and every index-only removal, through `commit-tree`/`update-ref`, so pre-commit and commit-msg hooks never run. `SKILL.md:25` says "never bypass a hook on your own judgment"; neither SKILL.md step 8 nor `by-hand.md` says the script can skip hooks. The shared-checkout hook-hazard text covers only the opposite case.
- Stale comments: `commit-pathspec.sh:5-6` and `:363` say SKILL.md step 8 "describes doing by eye" the per-hunk arithmetic; that procedure moved to `by-hand.md` step 8.
- Not filed, previously declined (see `dropped-findings.log` and done/pc-1035): the repo-wide "Joe" in skill prose versus bepy-skill-creator's no-hardcoded-names rule.

## Approach

Per duplicated block pick the authoritative copy (SKILL.md keeps the rule, the sidecar keeps the long form, or the reverse) and replace the other with a one-line pointer; add one sentence to SKILL.md step 8 and `by-hand.md` stating which commit paths skip hooks (or make the script refuse with a named `--force` when `core.hooksPath` is set); reword the two script comments. Keep `skills/release/test_pipeline_order.py` and `skills/commit/test_commit_pathspec.sh` green; the pointer wording `test_pipeline_order.py` pins must survive.

## Acceptance

`python ci/run_all.py` green; `grep -c "HARD ORDERING RULE" skills/close/*.md` shows one copy; SKILL.md step 8 names the hook-skipping paths.
