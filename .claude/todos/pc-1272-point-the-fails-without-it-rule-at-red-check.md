<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1247 mentions red-check only in passing (commit own-ranges), a different fix -->
# The "test that fails without it" rule doesn't name red-check.ps1, so sessions swap HEAD copies into the live shared tree instead

**Type:** skill-improvement
**Origin:** ai
**Summary:** A session proving a new test is red on pre-fix code reaches for `skills/close/red-check.ps1` instead of overwriting the fix files in the live checkout.

## Why

On 2026-10-29 (claude_usage_in_taskbar, chat "Chat open latency"), Claude needed to prove three new tests failed on pre-fix code. Each time it hand-rolled the check: copy the fix file aside, write `git show HEAD:<file>` over it in the live working tree, run the test, copy it back. That was 4 files at once in one of the three runs. Two other chats were active in the same checkout, so a peer build or commit during those windows could have picked up the reverted files. `red-check.ps1` exists to do exactly this in a detached worktree, but the only pointer to it is `refs/process-hygiene.md`, which the session never opened.

## Goal
Make the red-check tool discoverable at the moment the rule applies.

## Context
- Global `CLAUDE.md`, Testing & verification floor: "Every repo: each behavior change ships with a test that fails without it, written alongside the change". It names no tool for proving the "fails without it" half.
- `refs/process-hygiene.md:86` is the only place that points to `skills/close/red-check.ps1 -FixPaths ... -TestCommand ...`.
- `red-check.ps1` overlays the other uncommitted changes onto a HEAD worktree and leaves the fix paths at HEAD, so it never touches the live tree.

## Approach
- Add a short clause to that `CLAUDE.md` bullet, e.g. "(prove the red half with `skills/close/red-check.ps1`, never by reverting files in the live tree)". Keep it to one clause; the always-loaded token budget applies.
- Optionally, a hook that warns when a PowerShell/Bash command both writes `git show HEAD:` output over a tracked path and runs a test runner in the same call.

## Acceptance
- The CLAUDE.md bullet names `red-check.ps1`, and `python ci/run_all.py` (instruction token budget) passes.
