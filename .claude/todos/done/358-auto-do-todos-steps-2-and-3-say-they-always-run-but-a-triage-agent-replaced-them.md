<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# `/auto-do-todos` Steps 2-3 are marked "always runs", but a real run substituted a triage subagent

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/auto-do-todos` Steps 2-3 describe what a run should actually do when the invoking prompt
already demands a front-loaded question round, instead of leaving the run to deviate silently from a
step marked "no size exemption".

## Context

Observed 2026-08-16 in this repo. Joe's prompt was:

> "lets finish off all of the todos!!! /auto-do-todos but first go thru the todos and see if any of
> them require input from me, get all of that out of the way, and only then should you do anything"

`skills/auto-do-todos/SKILL.md` says Step 2 (`/cleanup-todos`) "runs on every run, no size
exemption", because it "is the only pass that dedupes, re-verifies premises against the tree, and
archives dead `ai`-origin todos, and Step 4's triage does none of those".

What the run actually did: dispatched ONE Step 4 triage subagent over all 18 todos, which read each
in full, re-verified premises against the tree (it caught todo 338 as superseded by commit `a7c09a6`
and verified todo 326's live hook state), and surfaced the duplicate id 338. It then went straight
to the question round. Steps 2 and 3 never ran as nested skills.

That was a defensible call and produced a good run, but the skill file does not sanction it, so the
run deviated from a rule marked absolute. This is the same contract-versus-practice shape as todo
347, where the file said invoke `/commit` per todo and every real run invoked it once.

The honest version of the tension: Joe's prompt asked for questions FIRST, and `/cleanup-todos`
plus `/batch-todos` are both work-doing passes that run before Step 5's question round. Obeying both
the prompt and the file is not possible as written.

## Approach

Decide which of these is true and write it down, rather than leaving a run to improvise:

1. **The Step 4 triage genuinely subsumes Step 2** when it is given every todo in full, in which
   case say so, and name the three things Step 2 uniquely provides (dedupe, premise re-verification,
   dead-`ai`-origin archival) as requirements the triage prompt must carry. This is the option the
   2026-08-16 run implicitly took, and its triage prompt did carry all three.
2. **Step 2 is genuinely irreplaceable**, in which case the skill must say what a run does when the
   invoking prompt demands questions before any work, since that is a direct conflict.

Whichever wins, add it to the "When each step runs" paragraph, which is where the no-size-exemption
claim currently lives.

Also check `/batch-todos`, which Step 3 delegates to, for the same conflict, and check whether the
Attended mode and Cleanout mode sections need the same qualifier: cleanout mode already fires Step 5
"immediately, up front, before any todo executes", which is closer to what Joe asked for and may
already be the right home for this behaviour.

## Acceptance

- A cold run reading Steps 2-3 knows, without improvising, what to do when the prompt asks for
  questions before any work.
- The three unique functions of `/cleanup-todos` are either guaranteed by whatever replaces it, or
  the substitution is explicitly forbidden.
- `/auto-do-todos` and `/batch-todos` agree.

## Notes

- Filed 2026-08-16 by `/close` from that run's own retrospective. The run itself flagged the
  deviation rather than hiding it.
- Related: [[347-auto-do-todos-commit-cadence-is-unfollowable-as-written]] in `done/`, the same
  literal-instruction-versus-real-run gap in the same file.
- Done 2026-08-17: took Approach option 1. skills/auto-do-todos/SKILL.md's 'When each step runs' paragraph drops the absolute 'no size exemption' claim and names two sanctioned invocations that MOVE Step 2's work instead of skipping it - questions-first (Step 4 triage runs first, and its prompt must carry Step 2's three unique functions as explicit requirements) and named-subset (dev names the ids; Steps 2-4 skipped, and Step 9 must say the backlog was not swept). Any other substitution is still a deviation and must be reported in Step 9. Checked skills/batch-todos/SKILL.md for the same conflict: it makes no always-runs claim, its Step 4 is a dry-run gate this skill already overrides, so it needed no change.
