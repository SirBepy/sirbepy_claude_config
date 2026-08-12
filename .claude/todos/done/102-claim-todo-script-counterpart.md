<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Add a claim-todo script to match complete-todo.ps1

**Type:** skill-improvement

## Goal

Claiming a todo should be one scripted call, the way completing one already is.
Right now completion has `~/.claude/skills/close/complete-todo.ps1` but claiming
has no counterpart, so every executor hand-rolls the protocol.

## Context

Observed 2026-08-04: a single session claimed three todos (90, 83, 89) and each
claim took three separate shell calls, because the global no-chaining rule
forbids `;`, `&&` and `|`:

1. `New-Item -ItemType Directory -Force .claims`
2. `Set-Content .claims/<id>.tmp-$PID` with session/pid/started content
3. `Move-Item` without `-Force` to `.claims/<id>.claim`

Nine shell calls for three claims, all boilerplate transcribed from
`ai-todos-format.md` each time. Every re-implementation is a chance to skip a
step, and the easy ones to skip are the ones that matter: the no-overwrite
rename that makes the claim a real mutex, the ~2s retry for the Windows
filter-driver false negative, and the stale-claim rule (mtime older than 4 hours
AND the pid no longer alive).

The heartbeat has the same problem: `(Get-Item <file>).LastWriteTime = Get-Date`
was typed out four separate times in that session.

## Approach

Add `~/.claude/skills/close/claim-todo.ps1` beside `complete-todo.ps1`, matching
its shape (`-Id`, optional `-RepoRoot`, clear success/failure output):

1. Self-heal `.claims/` existence and the `.git/info/exclude` lines, same as the
   contract requires at point of use.
2. Write the temp file, attempt the no-overwrite rename, retry once after ~2s on
   error before concluding anything.
3. On a losing race, evaluate staleness (mtime > 4h AND pid dead) and either
   reclaim or exit non-zero with "claimed by live session <pid>", so the caller
   can move to the next PLAN.md line.
4. Add `-Heartbeat` to touch an existing claim's mtime, so that stops being a
   hand-typed one-liner too.
5. Update `ai-todos-format.md`'s Claims section to name the script as the
   preferred mechanism, keeping the manual sequence as the documented fallback -
   exactly how the completion sequence is already worded.

## Acceptance

- Claiming a todo is one call, and `/pickup` plus any ad-hoc "do todo NN" path
  uses it.
- Losing a race to a live session is reported distinctly from a stale-claim
  takeover.
- The contract still documents the manual fallback for when the script is absent.

## Notes

Skill file involved: `~/.claude/skills/close/ai-todos-format.md` (Claims section)
plus the new script alongside `complete-todo.ps1`. `/pickup`'s SKILL.md step 2
just says "claim the id per the contract's protocol" and would not need editing
if the contract names the script.
- Dropped via /cleanup-todos 2026-08-11: already done - claim-todo.ps1 shipped; only the -Heartbeat convenience flag remained. Confirmed by dev 2026-08-11.
