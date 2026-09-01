<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=8, reconfirm-count=1, content-hash=5593f38c -->
<!-- duplicate-checked -->
<!-- 471, 490, 802, 318 and 383 all read in full on 2026-08-31. None is about the gate's verdict
     being bypassable; they share vocabulary only. Reasoning in Context below. -->
# A semicolon-chained commit runs even when the prefilter gate fails

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `/commit`'s prefilter gate from being bypassable by shell chaining, so a commit cannot land
while the gate is reporting a violation.

## Context

Happened 2026-08-31 in `../hubbub` - this session, not hypothetical. The command run was:

```
bash ~/.claude/skills/commit/prefilter-gate.sh <file> >/dev/null 2>&1; echo "GATE: $?"; git commit -m "..." -- <file>
```

`;` rather than `&&`, so `git commit` executed regardless. The gate had exited **1**: the diff was
6 comment lines in 21 added lines, over both the 4-line block cap and the ~25% ratio in CLAUDE.md's
Code Style section. The commit landed anyway (`973c2b7`). It was caught only because the exit code
was echoed and read afterwards; with output discarded, a violating commit would have shipped
silently.

The gate is not weak - it computed the right answer. The hole is that its exit code is advisory
once a `;` separates it from the commit.

Distinct from the hits the duplicate guard flagged: 471 is the secret scan producing false
positives, 490 is the test gate being too STRICT on pre-existing failures, 802 is output ordering,
318 (done) is em-dashes, 383 (done) is running the repo's test suite. This one is the opposite
failure mode - a correct verdict being ignored.

Also distinct from the commit-guard `PreToolUse` hook, which blocks raw `git commit` before a
session marker exists. That hook inspects the command string; it has no idea whether a prefilter
passed.

## Approach

1. **Move the check into the existing commit-guard hook** (recommended). It already intercepts
   `git commit` at `PreToolUse`. Have it run the same comment-noise computation over the staged
   pathspec and block on violation. This is the only option that does not depend on how the caller
   writes the shell command.
2. Make `/commit`'s SKILL.md mandate `&&` and forbid `;` between gate and commit. Cheap, but it is
   a rule about writing commands correctly, and this incident is exactly that rule being broken by
   an agent that knew it.
3. Have `prefilter-gate.sh` write a failure marker the commit-guard hook then refuses to commit
   past. More moving parts than option 1 for the same effect.

Options 2 and 3 are recorded so they are not re-derived, not because they are recommended.

## Acceptance

- A `;`-chained `git commit` after a failing prefilter is blocked, not merely warned about.
- A passing prefilter still commits with no extra friction or prompt.
- The commit-guard hook's existing session-marker behaviour is unchanged.

## Notes

- **This fix writes to `hooks/`, a hard stop for subagent dispatch**: `hooks/sensitive-file-guard.py`
  returns `ask`, and an `ask` inside a dispatched agent is a hard block with nobody to answer.
  Route to the main thread with Joe present, per `/autopilot`'s Hard Stops list.
- The offending commit was corrected in-session (comment trimmed to 4 lines, commit amended), so
  the repo is clean. This todo is about the hole, not that commit.
