<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=EASY, worth=8, reconfirm-count=1, content-hash=6d49250e -->
# /cleanup-todos verifies premises against whatever is checked out, and says so

**Type:** skill-improvement
**Origin:** ai

## Goal

`~/.claude-fibo/skills/cleanup-todos/SKILL.md` Step 4 tells the deep pass to re-verify an
`ai`-origin todo's premise "against the current tree". On a branch that is behind its trunk, "the
current tree" is the wrong universe, and the skill produces confidently wrong verdicts with real
`file:line` citations behind them. Step 4 should resolve the reference point BEFORE any verification,
and hand that ref to the subagents.

## Context

Reproduced at cost on 2026-08-18 in `C:\Users\tecno\Desktop\Projects\fibo`.

A `/cleanup-todos` run triaged 17 todos from branch `fix/frontend2-code-health-sweep`, which was **63
commits behind `origin/develop`**. Step 4's dispatch followed the skill text literally and verified
against the checkout. Result: all 17 came back `still_valid: true`, each with citations. Two were
wrong:

- todo `243` (decide the login logo size) - already settled; develop carried the original
  `h-[4.5rem]` and the branch's own later commit is what set `h-16`, which was the value the dev had
  asked to keep. Nothing to decide.
- todo `175` (persist review decisions once backend2 has the endpoint) - **moot**; develop's
  `50d974a5` states the purchase review batch was deleted deliberately, so the endpoint the todo
  wanted to request will never exist.

Cost: ~137k subagent tokens on the first pass, then a second full re-verification pass against
`origin/develop`. It was caught by the dev's instinct ("bro im so sure some of these are done... are
we on the right worktree/branch?"), not by the skill or by Claude.

Why the existing guardrails did not fire: the project memory on this
(`feedback-compare-against-origin-not-local-ref`) was written around git COMMANDS run against a bare
local ref, so a pass that greps files and reads `file:line` instead of running `git diff` reads as out
of its scope. The skill text is the actual enforcement point, and it currently says the opposite of
what is needed.

## Approach

1. In `cleanup-todos/SKILL.md` Step 4, before the chunk dispatch: compute and PRINT
   `git rev-list --left-right --count HEAD...origin/<trunk>` (trunk from the repo's own convention,
   e.g. `GIT_FLOW.md`, defaulting to `develop` then `main`). State the ahead/behind numbers in the
   Step 6 report so a reader can see which universe the verdicts describe.
2. If "behind" is non-zero, the dispatch prompt MUST tell each subagent to read
   `git show origin/<trunk>:<path>` rather than the working copy, and to say which ref each citation
   came from. If it is zero, the checkout is fine and nothing changes.
3. Add the failure mode to the skill's own text in one line, so the reason survives: a todo can be
   DONE or MOOT on the trunk while its premise still reads valid in a stale checkout.
4. Consider the same fix in `/batch-todos` step 5, which runs its own validity check on the same files
   and has the identical blind spot. Do not change it blind - read it first and confirm the wording.

## Acceptance

- Step 4 cannot dispatch without the ahead/behind count having been computed.
- A run on a branch behind its trunk cites `origin/<trunk>` in its evidence, and the Step 6 report
  states the drift.
- Re-reading the skill makes it obvious WHY, not just what to run.

## Notes

Filed from a Fibo project session, per the rule that findings about the global `~/.claude` tree belong
in this repo's own backlog. **Nothing in `~/.claude` was edited from that session** - the fix needs a
session actually opened here.

The same run produced a second, separate observation not filed as its own todo: `/cleanup-todos`
Step 4's `worth <= 4` auto-archive rule fired correctly on an absent-origin todo (`221`), and the
"salvage before archiving" step mattered - its endpoint contract had to be folded into todo `248`
first or it would have been lost. That part of the skill worked as written.
- dba9143: cleanup-todos and batch-todos now resolve the reference point (git rev-list --left-right --count) before re-verifying premises.
