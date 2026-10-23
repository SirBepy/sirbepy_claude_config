<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1157/1026/1046/1064/1073 are other commit-pathspec defects (slug matching, git-add exemption, partial staging, no-newline file, same basename); none covers argv length or large file counts, and no backlog file mentions "Argument list too long" -->
# commit-pathspec.sh fails with "Argument list too long" on a ~1000-file commit

**Type:** skill-improvement
**Origin:** ai

## Goal
`skills/commit/commit-pathspec.sh` commits a large generated-asset change (hundreds of new files
under one or two directories) instead of dying in the prefilter gate.

## Context
- mc_plugins_tag session 8a7c, 2026-10-08: one feature commit held ~970 files (576 generated PNGs,
  288 .mcmeta, 288 model .json under `server/resourcepacks/claudesmp-items/assets/claudesmp/{textures,models}/item`,
  plus ~15 code files). The pathspec named the two asset directories, not each file.
- The script expanded the directories to per-file paths during classification, which took ~20
  minutes. The prefilter step then printed
  `/c/Users/tecno/.claude/skills/commit/_prefilter-lib.sh: line 5: /mingw64/bin/git: Argument list too long`
  four times and exited 1 (`=== todo-ref.sh ===` was the last section). Windows' ~32K command-line
  limit is the likely ceiling, about 300 paths at ~95 characters each.
- Workaround used: by-hand fallback. `prefilter-gate.sh` was run on the ~20 text/code files only,
  `git add -- <dirs>`, then `git commit -m ... -- <dirs and files>` (commit 978d9b3 in mc_plugins_tag).

## Approach
- In `_prefilter-lib.sh` (line 5 builds the git call), pass paths through `git ... --pathspec-from-file=-`
  or `xargs`-style batching instead of argv. Same for any other helper that hands the full file list to one git call.
- Skip binary files before the prefilters build their file lists. They already print
  "skipped binary", but only after the list was built.
- Consider classifying a directory pathspec in one `git status --porcelain -- <dir>` call rather
  than per file, which is what made it take ~20 minutes.

## Acceptance
A scratch repo commit of 1000 new small files in one directory plus 2 edited text files, through
`commit-pathspec.sh -- <dir> <file> <file>`, finishes in under ~2 minutes with `[commit] committed`
and no "Argument list too long".

## Notes

- Done by /loop-todos cycle 2 on 2026-10-23: prefilter and git calls take NUL path files or argv-sized chunks, untracked diffs are batched through a throwaway index, binary skip is bulk. 1000-file tracked-dir commit: over 600 s and Argument list too long before, about 30 s after; skills/commit/stress_commit_pathspec_large.sh reproduces it. An Opus review found a backslash-path fail-open in the new split_path, fixed with a test.
