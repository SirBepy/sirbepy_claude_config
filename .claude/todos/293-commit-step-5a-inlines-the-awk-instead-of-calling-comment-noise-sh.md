<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /commit step 5a pastes the comment-noise awk inline, so sessions retype it instead of calling the script

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/commit` step 5a invoke the `comment-noise.sh` script that already exists, instead of embedding
the raw awk pipeline in the skill text.

## Context

Surfaced by the `/close` retrospective of the 2026-08-12 `windows_taskbar_widgets` session.

`skills/commit/comment-noise.sh` **already exists** (todo 290 cites it as the model to mirror for an
em-dash checker). But `skills/commit/SKILL.md` step 5a does not mention it. It instead pastes the
full awk one-liner into the skill body, prefixed with "Run this exact command, replacing `<files>`".

The predictable consequence: that session hand-assembled the awk pipeline **before all 20 commits**,
retyping ~12 lines of awk each time, because the skill text presents the pipeline as the interface.
The script was never called once. Every retype is also a chance to corrupt it, which has happened
before - see `done/13-commit-skill-comment-noise-awk-is-corrupted` and
`done/45-skill-arg-substitution-clobbers-awk-dollar-zero`, both caused by the pipeline living as
copy-pasted text rather than as a file.

This is the same class of problem as todo 290 (em-dash check hand-rolled per run), but the opposite
cause: 290 has no script, this one has a script nobody is pointed at.

## Approach

1. Read `skills/commit/comment-noise.sh` and confirm its actual interface - working-tree mode taking
   file paths, and whether it has the `--range <base>` mode todo 290 describes.
2. Replace step 5a's inlined awk block with a call to it, e.g.
   `bash "$HOME/.claude/skills/commit/comment-noise.sh" <files>`, keeping the existing "flagged means
   trim it now, do not ask" treatment and the pointer to `comment-noise.md` for the cap numbers.
3. Check whether the untracked-file pass currently described in step 5a (the `git status --porcelain`
   plus `git diff --no-index` loop for files not yet `git add`ed) is inside the script. If it is not,
   add it there rather than leaving half the logic in the skill text - a new file's comments are
   exactly the ones most likely to be over budget.
4. Do the same sweep for `/create-pr` step 2b, which `comment-noise.md` says carries a range-mode
   variant of the same command.
5. Grep the skills tree for any other pasted copy of this pipeline and point them all at the script.

## Acceptance

- `skills/commit/SKILL.md` step 5a contains no awk. It names the script and its arguments.
- Running `/commit` on a diff with a 6-line comment block still flags it; on a clean diff it prints
  nothing.
- An untracked new file with an over-budget comment block is still caught.
- No copy of the awk pipeline remains anywhere under `skills/` except inside the script itself.

## Notes

- Do not delete `comment-noise.md`. It is the single definition of the cap numbers (2 lines typical,
  4 hard per block, 25% ratio past 20 added lines) and both `/commit` and `/create-pr` defer to it.
- Related: [[290-em-dash-check-is-hand-rolled-every-run-instead-of-being-a-script]] proposes the
  sibling `em-dash.sh`. If both land, step 5a should call two scripts, not paste two pipelines.
