<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=1, reconfirm-count=1, content-hash=4ca81a2d -->
# Fix delegation-doctrine.md: repo-specific no-staging override + long-runner inline-only rails

**Type:** skill-improvement

## Goal

Two enforcement gaps in `~/.claude/refs/delegation-doctrine.md` (used by /delegate and /autopilot) exposed on 2026-07-28/29.

## Context

1. The doctrine mandates every builder prompt embed verbatim "Stage your changes but do NOT commit." In zng-app that staging blocked Joe's concurrent AI session (shared `.git/index`); he had to unstage by hand and correct Claude mid-session. A per-repo memory now exists ([[feedback-never-stage-leave-unstaged]]) but the doctrine still hard-codes the staging line, so every future dispatch re-creates the conflict. Bonus symptom: a subagent receiving the corrective "don't stage" SendMessage flagged it as possible prompt injection because it contradicted its verbatim dispatch instruction.
2. A long-running e2e agent ended its turn twice with non-answers ("waiting for monitor notifications") despite the doctrine's "Your final message is your entire return value / do not end your turn while sub-tasks are running" line - it burned ~450k tokens across stalls and needed two SendMessage resumes with explicit rails ("inline-only, no monitors, max 2 attempts per flow, BLOCKED counts as a result") before producing its report.

## Approach

Edit `C:\Users\tecno\.claude\refs\delegation-doctrine.md`:
- Replace the unconditional staging line with: default stage-don't-commit, EXCEPT when a project memory/rule says the index is shared - then "leave all changes unstaged" goes in the dispatch verbatim instead. Point at the zng-app memory as the example.
- Add a "long-running verification agents" clause to the builder-prompt requirements: forbid monitors/background-wait patterns in the subagent (work inline, bounded polling only), require a per-unit attempt cap with FAIL/BLOCKED as legitimate results, and require the full report as the final message every time the agent stops.

## Acceptance

- Doctrine text contains both changes; the staging paragraph explicitly defers to project-level no-staging rules.
- A dry read of /delegate + doctrine produces a dispatch prompt for zng-app that says "leave unstaged" without needing a mid-task correction.

## Notes

- Dropped via /cleanup-todos 2026-08-12: premise re-verified FALSE - refs/delegation-doctrine.md:45-48,108-110 already carry both the conditional staging line and the long-runner inline-only rail. AI-origin, auto-archived per dev standing instruction 2026-08-12 (no confirm gate for ai-origin todos).
