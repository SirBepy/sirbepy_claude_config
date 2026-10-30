<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped .claude/todos/ for "cannot invoke skills", "subagents never commit"; 1148 (done) is the commit-guard agent_id block, not the stale rationale text -->
# Sweep the remaining "subagents cannot invoke skills" claims left after builders started committing their own work

**Type:** skill-improvement
**Origin:** ai
**Summary:** Every doc and memory that still says subagents cannot load skills, or must never commit, matches the 2026-10-29 rule: builders commit their own work via `/commit`.

## Why

2026-10-29: a sonnet subagent loaded `/context-left` through the Skill tool, and a builder committed `9b74788` through `/commit`'s `commit-pathspec.sh` step with no hook or classifier denial. CLAUDE.md's Git Commits rule, `refs/builder-preamble.md`, `refs/delegation-doctrine.md`, `refs/process-hygiene.md` and the `hooks/commit-guard.py` deny message were updated in the same session. The files below were left alone because other sessions owned them at the time, or because they live in other projects' memory.

## Goal

No file still states the old rationale as fact.

## Context

Grep hits found 2026-10-29 (`grep -rn -i "cannot invoke skills\|subagents never commit"`):

- `skills/mega-todos/SKILL.md:387` - "You cannot invoke /commit as a skill" in the injected builder commit block. Mega-todos builders could now run `/commit` instead of the hand procedure; weigh that against its `barrier` default (`SKILL.md:88-97`, the classifier denying the per-commit marker write).
- `skills/cleanup-todos/SKILL.md:72` - "subagents cannot invoke skills".
- `skills/isolated-build/SKILL.md:62` - "helper skills and subagents never commit".
- `refs/debugging-method.md:9`, `refs/refactoring-method.md:9` - give "subagents cannot invoke skills" as the reason those are refs, not skills.
- Project memories under `projects/*/memory/`: sirbepy-roblox `feedback_subagents_never_commit.md` + its MEMORY.md line 18, zng-biller `feedback_commit_granularity.md:17` + MEMORY.md line 95, claude-usage-in-taskbar `project_repo_coordination_channel.md:93`, pomodoro-overlay `feedback_execution_branch_autopick.md:14`. These load in those projects' sessions and contradict the new rule.

## Acceptance

- The grep above returns no hit outside `.claude/todos/done/`, `.for_bepy/` and history-only incident text.
- `python ci/run_all.py` passes.

## Notes

- 2026-10-30 (`/global-claude-folder-audit` run, unattended): fixed `skills/cleanup-todos/SKILL.md:72`, `skills/isolated-build/SKILL.md:62`, `refs/debugging-method.md:9`, `refs/refactoring-method.md:9`. The audit's staging-line sweep landed in the same commit: autopilot, delegate, auto-do-todos (all three guard-accepted staging lines, default first), project-onboarding + its 6 flutter prompts ("Leave all changes unstaged" variant, parallel subs), bepy-skill-creator's FAIL rule, `snippets/auto-branch-main.md`, `snippets/auto-execution-mode.md`, and the stale "Agent has no `effort` param" text in `refs/delegation-doctrine.md` and autopilot.
- Still open: `skills/mega-todos/SKILL.md:387` (weigh against its `barrier` default, deliberately left), `skills/isolated-build/land.ps1:19` comment ("helper skills never commit" wording), `CLAUDE.md:150` ("Agent tool takes no effort parameter", now false: CLAUDE.md edits wait for the dev because of its 24-token CI headroom), and the project memories listed in Context.
