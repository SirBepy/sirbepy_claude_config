<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=7, reconfirm-count=1, content-hash=cf565107 -->
<!-- duplicate-checked: done/37 and done/216 settled that the staging line is ALWAYS included (kept here); done/871 checked both variants are named. None addresses which variant read-only dispatches paste, which is this todo's subject. -->
# READ-ONLY dispatches still carry "Stage your changes", which invited a `git add -A`

**Type:** skill-improvement
**Origin:** ai

## Goal

A `READ-ONLY DISPATCH` subagent should never be told to stage anything. Keep the always-present
staging line (per done/37's decision) but make read-only templates paste the "Leave all changes
unstaged" variant plus "never run `git add`", instead of "Stage your changes".

## Context

2026-10-08, pomodoro-overlay overnight `/loop-todos` run: the `/cleanup-memory` Step 4 deep-pass
subagent got a read-only preamble (`READ-ONLY DISPATCH` + "Stage your changes but do NOT commit.
The main agent will run /commit after your report-back."). It ran `git add -A` once, staging two
unrelated untracked files (`.playwright-mcp/page-*.yml`, `src-tauri/.cargo/config.toml`), then
noticed and unstaged them with `git restore --staged`. No harm landed, but in a shared-index repo
`git add -A` stages a peer's work into the index.

The contradiction is in the templates: `hooks/dispatch-preamble-guard.py` accepts either "Stage your
changes but do NOT commit" or "Leave all changes unstaged", and the read-only dispatch blocks seen
this session (`skills/code-check/SKILL.md` "The analysis runs in a fresh subagent, always",
`skills/review-unpushed/SKILL.md` Step 3) paste the "Stage your changes" variant.

## Approach

- In the read-only dispatch blocks of `skills/code-check/SKILL.md`,
  `skills/review-unpushed/SKILL.md`, and the read-only guidance in `refs/builder-preamble.md`
  (also check `skills/cleanup-todos/SKILL.md` and `skills/cleanup-memory/SKILL.md`, which defer to
  it), use "Leave all changes unstaged. Never run `git add`." as the staging line.
- Optionally make `hooks/dispatch-preamble-guard.py` reject "Stage your changes" when
  `READ-ONLY DISPATCH` is also present, with a self-test.

## Acceptance

- No read-only dispatch template in `~/.claude` contains "Stage your changes".
- `python ci/run_all.py` green.

## Answers 2026-10-08

- Joe, 2026-10-08 (todo-questions chat): templates AND guard. Read-only templates paste "Leave all changes unstaged. Never run `git add`.", and `hooks/dispatch-preamble-guard.py` rejects a `READ-ONLY DISPATCH` prompt that also says "Stage your changes", with a self-test.
