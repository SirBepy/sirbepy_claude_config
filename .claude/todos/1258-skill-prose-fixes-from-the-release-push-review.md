<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1065 (flutter-bump push gate), 1251 (pretty-readme visual learnings), 02 (auto-commit hook), 1004 (commit-pathspec flags), 1005 (push read gate) are different defects in the same files -->
# Skill prose fixes from the 2026-10-28 push review: auto-respawn handoff, pretty-readme dispatches, batch-todos callers, commit 7a lock claim

**Type:** task
**Origin:** ai

## Goal
Five small prose defects in skill files are fixed so each skill does what it says when followed literally.

## Context
Found by the 2026-10-28 pre-push code-check and per-commit review (release session).
1. `skills/auto-respawn/SKILL.md:26-28`: "The handoff prompt's first instruction must be to run `/auto-respawn` again". The skill has `disable-model-invocation: true`, so a successor model cannot reach it through the Skill tool; the opt-in silently never lands. `skills/loop-todos/SKILL.md` Phase 4 has the working pattern: the handoff prompt's FIRST characters are the literal slash command.
2. `skills/pretty-readme/SKILL.md:35` (Step 1 Explore subagent) and `~:125` (Step 7 secret scan subagent): no `model: 'sonnet'` pin and no canonical preamble; bepy-skill-creator's FAIL checklist requires both.
3. `skills/mega-todos/SKILL.md:60` tells the model to run `/cleanup-todos` and `/batch-todos` unattended, but batch-todos carries `disable-model-invocation: true` (e0cc2a9); a Skill-tool call is refused. auto-do-todos was fixed in 834592b to read it as a file; mega-todos was not. Also `skills/batch-todos/SKILL.md:10-12` "Trigger: `/batch-todos` only. Never auto-invoke" contradicts its description "Internal step for /auto-do-todos".
4. `skills/close/ai-todos-format.md:4,413` still tell the dev to trigger via `/batch-todos`.
5. `skills/commit/SKILL.md` step 7a states the daemon commit lock (120 s poll, 5 min expiry) means a peer commit "cannot sweep this session's files". UNVERIFIED lock numbers, and `commit-pathspec.sh` runs `git add` on untracked files before the commit, outside the lock, so the claim is too strong.

## Approach
1: make the handoff prompt start with the literal `/auto-respawn` line. 2: add the READ-ONLY DISPATCH preamble and model pin. 3: mega-todos reads batch-todos as a file like auto-do-todos; align batch-todos' Trigger line with its description. 4: update the two references. 5: soften to what is verified, or verify the lock numbers against the Conductor daemon source and cite it.

## Acceptance
Each of the five points is fixed or explicitly declined with a reason in this file's Notes.
