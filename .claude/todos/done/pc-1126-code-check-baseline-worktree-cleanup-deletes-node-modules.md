<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=9, reconfirm-count=1, content-hash=f2af3e1e -->
<!-- duplicate-checked: done/40 built safe-remove-worktree.ps1 and done/946 put it in the builder preamble; this is the /code-check dispatch block, which pastes neither, and the hazard recurred through it -->
# A /code-check reviewer's baseline worktree cleanup left the main checkout's node_modules half deleted

**Type:** task
**Origin:** ai

## Goal

A `/code-check` reviewer that builds a scratch baseline worktree with a `node_modules` junction to
the main checkout can never delete files inside the main checkout's `node_modules` when it cleans up.

## Context

Seen 2026-10-07 in fibo (`C:\Users\tecno\Desktop\Projects\fibo\frontend2`). A read-only `/code-check`
subagent ran `prettier --check` in a `git worktree add` baseline at `C:\tmp\fibo_baseline_wt`, with a
`node_modules` junction to `frontend2/node_modules`, then reported removing the worktree and the
junction. Right after it, the main checkout's `frontend2/node_modules/.bin` was gone and 59 test
files failed with `Cannot find module '@asamuzakjp/css-color'`; `npm install` from the lockfile
restored them ("added 120 packages"). Tests were green (1067) minutes before the dispatch.

The same symptom (`.bin` shims gone, `@asamuzakjp/css-color` missing, `npm install` adding 120
packages) hit a builder earlier the same day, after a previous `/code-check` reviewer had rerun knip
in a worktree (fibo todo 297's Context). UNVERIFIED which exact removal command followed the
junction; the reviewer's transcript would show it.

done/40 built `safe-remove-worktree.ps1` and done/946 put it in `refs/builder-preamble.md`, but the
dispatch block in `skills/code-check/SKILL.md` ("The analysis runs in a fresh subagent, always")
pastes only three marker lines, not the preamble, so its reviewer never sees the rule.

## Approach

1. Read the reviewer transcript (fibo session dff4aee1, agent a1b364eb7283bd638) and find the
   removal command.
2. Make `/code-check`'s dispatch block carry the worktree-removal rule (or the whole builder
   preamble with its read-only opt-out).

## Acceptance

- A `/code-check` reviewer that builds a baseline worktree with a node_modules junction leaves the
  main checkout's `node_modules` untouched (file count before and after).

## Notes

- Completed 2026-10-08 (loop-todos cycle 1): root cause traced to git worktree remove --force after a node_modules junction (fibo session dff4aee1); code-check SKILL.md reviewer dispatch now carries the worktree-removal safety paragraph.
