<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: the hits (1006, 1011, 1031, 321, 784, all done) cover preamble markers, todos writes, scratch dirs and the global edit ban, none the worktree's base commit -->
# Agent `isolation: "worktree"` checks out origin's tip, not local HEAD; builder preamble doesn't say so

**Type:** skill-improvement
**Origin:** ai

## Goal

A builder dispatched with `isolation: "worktree"` works on the same code the orchestrator sees, not an older pushed commit.

## Context

mc_plugins_tag, session c82d, 2026-10-09: five builders dispatched with `isolation: "worktree"` all started at `6032f7c` (origin/main, the last push) while local main was at `b0a4c20`, 17-121 commits ahead. One builder noticed (its target file was the 191-line pre-feature version) and fast-forwarded; the orchestrator then messaged the other four mid-run. Builders that had not noticed would have edited code that no longer existed on main (one task's files, `TownEviction`/`ScatterFallback`, did not exist at all on the stale base). The orchestrator only caught it because one report said so.

The preamble (`refs/builder-preamble.md`) and `refs/delegation-doctrine.md` say nothing about the worktree's base commit.

## Approach

Add one line to the canonical preamble block (or a placeholder filled only for worktree-isolated dispatches): "If you are in an isolated worktree, run `git merge --ff-only <the orchestrator's branch>` first and confirm `git merge-base --is-ancestor <branch> HEAD`; the worktree may start from the remote's tip, not local HEAD." Optionally note in delegation-doctrine that repos with many unpushed commits need this.

## Acceptance

- The preamble carries the line; a worktree-isolated dispatch in a repo with unpushed commits starts its work on local HEAD.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): builder-preamble has a <WORKTREE_LINE> placeholder (ff-only merge of the orchestrator branch plus merge-base check, filled only for isolation worktree dispatches) and a doctrine note; dispatch-preamble-guard tests ALL PASS.
