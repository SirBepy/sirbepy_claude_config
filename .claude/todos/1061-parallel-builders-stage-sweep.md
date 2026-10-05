<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: hits are about lint-staged, push of a clean tree, clockify, scout file sets and the screenshot reminder; none covers parallel builders' staged files leaking into another chunk's commit -->
# Parallel builders in one working tree: staged files leak into the wrong commit

**Type:** skill-improvement
**Origin:** ai

## Goal

When an orchestrator runs two or more builder subagents at once in the same working tree, one builder's staged changes can never ride into the commit for another builder's chunk.

## Context

Incident 2026-10-01, sirbepy_assistant: two parallel builders (inbox/rail and reader) both got the default staging line "Stage your changes but do NOT commit". The orchestrator committed the reader chunk using `git diff --cached --name-only` as the pathspec for `commit-pathspec.sh`. That list included 4 `git rm` deletions the OTHER builder had staged mid-task (tiers.dart, account_filter.dart, tier_section.dart, tiers_test.dart). The result was commit 96c1208, which carries another chunk's deletions and leaves HEAD uncompilable (main.dart still imported a deleted file) until the second builder's commit landed. `refs/builder-preamble.md` already has the "Leave all changes unstaged" variant, but it's scoped to repos that share an index with concurrent SESSIONS. It doesn't cover the more common case of the orchestrator's own parallel builders.

## Approach

In `refs/builder-preamble.md`'s placeholder table and `refs/delegation-doctrine.md`'s dispatch discipline, state that any dispatch running concurrently with another builder in the same tree must use the "Leave all changes unstaged" line, and must list its changed files in the report. The orchestrator then commits by the builder's reported file list, never by `git diff --cached`. Consider having `commit-pathspec.sh` warn when the pathspec includes staged deletions the caller did not name explicitly.

## Acceptance

Both refs say it, and a dry read of the doctrine leaves no path where `git diff --cached` is the pathspec source while parallel builders run.
