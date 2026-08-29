<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=8, reconfirm-count=1, content-hash=7abc9b02 -->
<!-- duplicate-checked -->
# code-check's `uncommitted` scope silently misses untracked new files

**Type:** skill-improvement
**Origin:** ai

## Goal

Fix `skills/code-check/SKILL.md`'s scope-resolution table so the `uncommitted` arg (and `/close`
Phase 2, which defaults to it) actually covers brand-new files, not only modifications to files
git already tracks.

## Context

Hit 2026-08-25 in `honeymoon-tools` during a `/close` run. The session had written 9 new `.mjs`
scripts under `src/`, none yet `git add`ed. Phase 2 resolved scope via the documented command:

```
git diff HEAD --name-only --diff-filter=ACM
```

That returned nothing. `--diff-filter=ACM` only matches paths already present in the git index in
some form (staged additions, copies, modifications) - a genuinely untracked file has no index
entry at all, so `git diff HEAD` cannot see it regardless of the filter. Confirmed directly:
`git status --porcelain -- src/` listed all 9 files as `??` (untracked) in the same repo state
where the documented command returned empty.

Silently reviewing zero files when 9 real, substantial (295 lines total) code files sat
uncommitted is worse than erroring: `/close`'s Phase 2 would have printed "No code files in
scope." and nobody would know coverage was wrong unless they manually cross-checked, which this
session only did because the mismatch was suspicious on its face.

## Approach

- Change the `uncommitted` row's command to something that includes untracked files, e.g.
  `git status --porcelain --diff-filter=ACM` is not a real flag combination since `--diff-filter`
  is a `git diff`-only option - the actual fix is likely two commands unioned: `git diff HEAD
  --name-only --diff-filter=ACM` (tracked changes) plus `git ls-files --others
  --exclude-standard` (untracked, respecting .gitignore).
- Apply the same check to any other scope row that assumes `git diff` alone is sufficient.
- Note in the skill that "uncommitted" should mean "everything `git status` would show as dirty,"
  not "everything `git diff` can see" - those are not the same set.

## Acceptance

- A repo with only untracked new files (no modifications to tracked ones) resolves `uncommitted`
  scope to that file list, not to an empty one.
- `/close` Phase 2 no longer prints "No code files in scope." when untracked code files exist.

## Notes

Worked around manually this session by resolving the file list via `git status --porcelain`
instead of the documented command before dispatching the review subagent. That workaround is not
itself a fix - the documented default is still wrong for the next session that follows it as
written.
