<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: pc-1297 is about pipes inside quotes, a different guard bug -->
# Hook false positives that cost retries in a release

**Type:** task
**Origin:** dev
**Summary:** Four hook behaviours blocked correct commands during the 0.2.146 release and each cost a retry.

## Goal
Remove or document the four blocks so a release run does not trip them.

## Context
Seen 2026-11-06 in claude_usage_in_taskbar:
- `hooks/cargo-test-pipe-guard.py` blocked `cargo build ... | Select-Object -Last 5` (correct in spirit) but its message and the commit skill both steer toward running unpiped; fine, but the PowerShell variant was not obvious.
- `hooks/dev-server-guard.py` matched `pnpm exec vite build` as a long-lived dev server (`vite` in the string). A one-off `vite build` exits.
- `commit-pathspec.sh` refuses a `Co-Authored-By` trailer, while the harness attribution reminder says to add one; the conflict is only learned by failing once.
- `hooks/push-read-gate.py` blocks the session's first push until `snippets/auto-commit.md` is read, even in a gate that is itself the user's push ask.

## Approach
Make dev-server-guard skip `vite build`/`vite preview --help`-style one-shots; note the no-trailer rule in the commit skill's step 8 so it is read before the first attempt; leave the push-read-gate alone unless the gate-chat path can pre-read the file.

## Acceptance
`pnpm exec vite build` runs without a block, and the commit skill states the no-trailer rule where the message is composed.
