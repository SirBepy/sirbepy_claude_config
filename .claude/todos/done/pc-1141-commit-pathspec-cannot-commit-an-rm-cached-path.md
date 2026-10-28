<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=HARD, worth=7, reconfirm-count=1, content-hash=7b41965e -->
<!-- duplicate-checked: 2026-10-08; done/1101 is untracked files in a tracked dir, not an index-only removal -->
# commit-pathspec.sh cannot commit a `git rm --cached` untracking

**Type:** skill-improvement
**Origin:** ai

## Goal
Untracking a file that stays on disk (`git rm --cached <path>`, usually alongside a new `.gitignore`
line) commits through `commit-pathspec.sh` like any other change.

## Context
2026-10-08, loop-todos final review: after `git rm --cached skills/clockify-reconciliator/.impeccable/hook.cache.json`
plus a `.gitignore` line for it, `commit-pathspec.sh ... -- .gitignore <that path>` stopped with
`[commit] ERROR: could not stage untracked file <path>`. The script classifies a path that is on
disk but not in the index as untracked and runs `git add` on it, which the new ignore rule refuses.
A plain `git commit -- <path>` would not help either: a pathspec commit takes the working-tree
state, so it would re-add the file. The workaround used was deleting the (regenerable) file from
disk so the path classified as deleted.

## Approach
In the pathspec classification, treat a path that is in HEAD, absent from the index and present on
disk as an index-only removal: keep it out of the `git add` step, and commit it from the index
(for example `git commit --include` semantics are wrong here; check whether a temporary index or a
separate `git commit -- <path>` after `git rm --cached` inside the script is the cleanest). Add a
`test_commit_pathspec.sh` case for it.

## Acceptance
- `git rm --cached f` then `commit-pathspec.sh ... -- .gitignore f` commits the removal, and `f` is
  still on disk and untracked afterwards.
- `bash skills/commit/test_commit_pathspec.sh` passes.

## Notes

- Done 2026-10-08: commit-pathspec classifies a HEAD-tracked, index-absent, on-disk path as index-removed and, when one is present, builds the commit tree in a throwaway index (read-tree HEAD, replay each path, write-tree, commit-tree, old-value-checked update-ref), so the untracking lands and the file stays on disk. Test r51.

## Answers 2026-10-08

- Joe, 2026-10-08 (todo-questions chat): approved to build as written.
