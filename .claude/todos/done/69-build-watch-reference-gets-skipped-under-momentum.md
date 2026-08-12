<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# `/commit push*`'s pointer to `build-watch.md` gets skipped - fold the launch step inline or make the pointer unmissable

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop a session from hand-rolling its own CI-watch loop instead of using `skills/commit/watch-build.ps1`
+ its documented reporting discipline, when `/commit push`/`pushbump`/`pushnbump` only points at
`build-watch.md` via a parenthetical instead of inlining the step.

## Context

Session 2026-08-09/10 (`claude_usage_in_taskbar`, session id `b864b403-d51d-41fc-b8c5-5f2fd41056ed`):
after two separate `/commit pushnbump` runs, the session improvised its own `gh run list --limit 1`
polling loop in a background Bash call instead of launching `skills/commit/watch-build.ps1` per
`skills/commit/build-watch.md`. Both times this hit exactly the failure mode that file's own
"Reporting discipline" section warns against verbatim: *"never `--limit 1`"* - a push triggers both
a "Tauri Release" and an "Auto-Fix Release Failure" workflow row, and `--limit 1` can grab either one
depending on ordering. Both times the session had to manually re-run a full `gh run list` filtered by
`workflowName` to get the real answer, after already reporting (or nearly reporting) the wrong row's
conclusion as the build result.

The `/commit` skill's own text (`skills/commit/SKILL.md`) only references the watcher via "After a
successful push, run the **Build watch** (see `skills/commit/build-watch.md`)" - a pointer, not
inlined instructions. Under session momentum (mid-feature, wanting to report back quickly), the
pointer got skipped entirely rather than followed, twice, by the same session.

## Approach

Two options, pick one (or both):

1. **Inline the watcher-launch step directly into `/commit`'s `push`/`pushbump`/`pushnbump` sections**
   instead of a "(see build-watch.md)" pointer - the exact `& "...\watch-build.ps1" -Branch <branch>
   -RepoPath <path>` command and the "announce and move on" line, so there's no separate file to skip
   reading under momentum. `build-watch.md` stays as the deeper reference for the gated-auto-fix /
   BUILD_RESULT-parsing logic, which is genuinely too long to inline.
2. Alternatively (cheaper, less robust): bold/flag the build-watch pointer harder, e.g. prefix it
   "**MUST read before pushing:**" - but this session shows a plain parenthetical pointer is already
   not enough, so option 1 is the more reliable fix.

## Acceptance

- A future `/commit push`/`pushbump`/`pushnbump` run launches the real `watch-build.ps1` (or reads
  `build-watch.md` first) rather than an ad hoc `gh run list --limit 1` loop, without needing to be
  reminded.
- `build-watch.md`'s "never `--limit 1`" rule stays intact for the deeper reference material.

## Notes

- Duplicate of 75 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
