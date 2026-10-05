<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no other todo covers the coverage-check basename false positive -->
# commit-pathspec.sh coverage check refuses on a same-named file in an unrelated directory

**Type:** skill-improvement
**Origin:** ai

## Goal
The staged-pathspec coverage check only refuses on the move shape it exists for, not on any staged file that shares a basename with a pathspec file.

## Context
2026-10-03, mc_plugins_tag (session cf279864). A pathspec commit of `tag/src/main/resources/config.yml` (plus other tag/ files) was refused with `[coverage-check] REFUSED: path(s) matching the pathspec by directory or basename are not in it (possible half-committed move) ... names/src/main/resources/config.yml`. That names/ file was another builder's unrelated staged edit, not half of a move. `skills/commit/SKILL.md` step 8 defines the move shape as a staged path NOT in the pathspec that "shares a directory with a path that IS in the pathspec", and says an unrelated directory should only warn. Matching by basename turns every `config.yml`/`plugin.yml`/`build.gradle.kts` in a multi-module repo into a false positive, so `--force coverage` became routine for the rest of the session (it was passed on 5 commits), which dulls the check for real half-moves.

## Approach
In `skills/commit/commit-pathspec.sh` (coverage-check step), drop the basename match, or require the staged path to be an actual rename partner (`git diff --cached --name-status -M` R/D+A pair whose other side is in the pathspec). Keep warning, not refusing, for unrelated staged paths, per SKILL.md.

## Acceptance
- Repro: stage `a/config.yml`, commit `b/config.yml` by pathspec: warns, does not refuse.
- `git mv x/f.md y/f.md` then pathspec only `y/f.md`: still refuses.
- `python ci/run_all.py` green.
