<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1161 is arg-list-too-long, 1164 is a patch-apply failure, 1167 is a WriteAllText cwd bug, 1026 is the git-add-before-pathspec exemption, 1033 is foreign-hunk-check on a pure deletion - none of these is the pathspec CLASSIFIER itself misreading an absolute path as a deletion for a file that is actually modified and present -->
# commit-pathspec.sh misclassifies a live file as deleted when given an absolute forward-slash path

**Type:** skill-improvement
**Origin:** ai

## Goal

`skills/commit/commit-pathspec.sh` classifies a pathspec entry correctly regardless of whether the
caller passes an absolute path or a repo-relative one.

## Context

In `mc_plugins_tag` (Windows), running:

```
bash skills/commit/commit-pathspec.sh --expect-branch main --expect-sha <sha> \
  -m "..." -- "C:/Users/tecno/Desktop/Projects/mc_plugins_tag/treemod/src/main/java/dev/sirbepy/mc/treemod/HubScreen.java"
```

printed `HubScreen.java: deleted-unstaged (excluded from overlap-check/foreign-hunk-check - nothing
left to diff)` for a file that was modified, present on disk, and showed `M` in `git status
--porcelain`. The commit then refused with `[coverage-tests-check]` (expected, separate issue) but
never reached the overlap/foreign-hunk checks because the script had already decided there was
"nothing left to diff".

Re-running the identical command with a repo-relative path instead
(`treemod/src/main/java/.../HubScreen.java`) classified it correctly as `live` and the full
pipeline ran as expected.

Session: mc_plugins_tag, 2026-10-17, implementing the /class hub Browse-classes feature.

## Approach

Find wherever the script's pathspec classifier compares the caller-given path against `git status
--porcelain`/`git diff --name-status` output (likely a string-equality or prefix check) and make it
resolve the path (absolute or relative) against the repo root the same way `git` itself would,
before comparing - e.g. via `git ls-files --full-name` or `realpath --relative-to=<repo-root>`,
rather than comparing the caller's literal path string against git's relative-path output.

## Acceptance

The repro command above, run with the absolute `C:/...` path, classifies the file as `live` (not
`deleted-unstaged`) and the overlap-check/foreign-hunk-check steps actually run against it.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): commit-pathspec.sh normalizes absolute pathspecs (and --own-range keys) to repo-relative via cygpath -m before classification; test RED then GREEN.
