<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=6, reconfirm-count=1, content-hash=1076065d -->
# code-style/tauri.md's 300-line split rule should exclude colocated Rust test modules

**Type:** task
**Origin:** ai

## Goal
Clarify the file-size guidance in `~/.claude/code-style/tauri.md` so it does not read as contradicted by the codebase it governs.

## Context
Surfaced by a `/code-check` run on claude_usage_in_taskbar on 2026-08-14, while reviewing a newly split `src-tauri/src/daemon/hooks_server/question.rs`.

`tauri.md` states "Any file past ~300 lines should split into a subfolder." Rust convention, followed consistently in that repo, is to colocate unit tests in a `#[cfg(test)] mod tests` at the bottom of the same file. `question.rs` is about 395 lines, roughly 205 of which are that test module, so the production code is under 200 lines and there is no split seam that does not fight the codebase's own convention. Nearly every file under `hooks_server/` is in the same position.

As written the rule flags well-structured files, which means reviewers either raise findings nobody will act on or quietly learn to ignore the rule. Both outcomes are worse than the rule not existing. Note this is specifically a Rust problem: for TypeScript, where tests live in a separate `tests/` tree, the raw line count is already the right measure.

## Approach
Amend the sentence in `~/.claude/code-style/tauri.md` to say the threshold counts production lines only, excluding a colocated `#[cfg(test)]` module, and note that TypeScript files are measured whole since their tests live elsewhere. Keep it to one or two sentences; do not restructure the doc.

## Acceptance
The rule, read cold against `src-tauri/src/daemon/hooks_server/*.rs`, no longer flags files that follow the repo's established test-colocation pattern.
