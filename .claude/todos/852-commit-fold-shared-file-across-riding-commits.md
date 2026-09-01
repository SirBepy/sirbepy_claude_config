<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# /commit fold: handle a file edited by multiple riding commits

**Type:** skill-improvement
**Origin:** ai

## Goal

The fold recipe in `skills/commit/SKILL.md` (`/commit fold <sha>`) recommits riding commits "with
its own unchanged file list" by pathspec, but a pathspec commit takes the file's CURRENT
working-tree state. When the same file is edited by two or more riding commits, the earlier
recommit silently absorbs the later commits' hunks and the patch-diff verification fails (or worse,
passes unnoticed if step 4 is skipped). Document the intermediate-restore technique.

## Context

Hit twice on 2026-08-31 in zng-app: `e2e/run-all.js` was edited by both the sc-55209 and sc-55220
commits riding above the fold target. The working fix, applied both times: before each intermediate
recommit, `git checkout <original-sha> -- <shared-file>` to restore that commit's own state of the
file, commit by pathspec, then restore the next state (or re-apply the tip edit) before the final
commit. Patch-diff verification then comes back byte-identical.

A second gap in the same recipe: it verifies riding commits via `git show` patch-diff, which is
exactly what catches the absorbed-hunk failure - but nothing in the recipe warns that the failure
mode EXISTS, so a session that hasn't hit it will walk into it on the first shared file.

## Approach

Edit `~/.claude/skills/commit/SKILL.md`'s "/commit fold" recipe step 3: add the shared-file rule -
detect files appearing in more than one riding commit's file list (`git show --name-only` overlap),
and for each intermediate recommit restore the shared file to that commit's own blob via
`git checkout <original-sha> -- <file>` first. Note the final commit needs the tip state restored
(re-apply or checkout the pre-fold tip sha).

## Acceptance

- The fold recipe names the shared-file hazard and the per-commit restore step.
- A future fold over a shared file produces byte-identical patch-diffs for riding commits without
  the executor re-deriving the technique.
