<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: audit bundle 9 -->
# Pilot new native Claude Code features against the custom setup

**Type:** task
**Origin:** dev
**Summary:** Try a few recent native Claude Code features side by side with the custom skills they might simplify, and keep only what wins.

## Why

Joe accepted this bundle from the 2026-10-30 `/global-claude-folder-audit` run. The research slice found these in primary sources (Claude Code CHANGELOG and docs), and the rules refuter re-confirmed each exists.

## Goal

Evidence, not a rewrite: each pilot ends with a keep / adopt / drop note.

## Context

- Native `/code-review` as the single-pass engine inside `/review-unpushed` (which slices commits into a sonnet fan-out). UNVERIFIED whether `/code-review` takes a commit list.
- `/goal` (a Stop-hook wrapper with an evaluator model) for the termination logic of `/loop-todos` and `/autopilot`.
- `CLAUDE_CODE_SUBAGENT_MODEL=sonnet` in `settings.json` env, plus `ask` rules for `Agent(model:opus)` / `Agent(model:fable)`, to make the "subagents are sonnet" rule mechanical. `hooks/dispatch-preamble-guard.py` already requires an explicit `model`. UNVERIFIED: whether the ask rule fires under auto mode; canary-test first.
- Native auditors as a cross-check before the next `/global-claude-folder-audit`: `/skill-doctor`, `/doctor prompt-audit`, `claude plugin validate ~/.claude/skills`.
- Already established as NOT duplicated natively (keep): `/respawn`, `/auto-respawn`, `/handoff`, the Silent output style, the todo backlog with claims, `/recall`, `/supervised-run`, `/sleep-when-done`.

## Approach

One pilot at a time, each in a scratch or low-stakes repo, A/B against the current skill on the same input. Record results in this todo's Notes.

## Acceptance

- Each of the four pilots has a recorded keep/adopt/drop verdict with the evidence.
