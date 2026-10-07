<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=EASY, worth=8, reconfirm-count=1, content-hash=b2bf33cb -->
<!-- duplicate-checked: 2026-10-06; done/265 and done/279 are the same shape for the commit-guard marker, not the push-gate mark. No open todo covers this. -->
# /commit's Pre-push gate should say the push-gate mark runs in its own tool call

**Type:** skill-improvement
**Origin:** ai

## Goal
`skills/commit/SKILL.md`'s "Pre-push gate" step 3 states that `push-gate.py mark` and `git push`
must be separate tool calls, so a session never loses a round trip to a denied chained push.

## Context
2026-10-06, this repo: `python hooks/push-gate.py mark ... && git push` in one Bash call was denied
by `hooks/push-gate.py` itself ("HEAD 8bc2fd5 ... has not been cleared for push"). The PreToolUse
hook inspects the whole command string before any of it runs, so the mark has not been written yet
when the hook checks for it. Same mechanism as the commit-guard session marker, which
`skills/commit/SKILL.md`'s opening section already documents ("in its OWN tool call, never chained
with the commit").

## Approach
In step 3 of the "Pre-push gate" section, add: run the `mark` command as its own tool call, then
`git push` in the next one; chaining them with `&&` or `;` is always denied.

## Acceptance
- The Pre-push gate section says so explicitly.
- `python ci/run_all.py` passes.
