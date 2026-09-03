<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# /commit's interactive unpushed-overlap gate is unusable once the unpushed stack is deep

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/commit` step 8's unpushed-overlap check a workable interactive behaviour when the branch is
many unpushed commits deep, instead of a per-commit question the dev cannot usefully answer.

## Context

Surfaced 2026-09-01 in `C:\Users\tecno\Desktop\Projects\windows_taskbar_widgets`, during a long
`/auto-do-todos` run that produced 10 commits in one interactive session. Joe had explicitly chosen
to keep everything local, so the branch sat 20+ commits ahead of its upstream the whole time.

`skills/commit/SKILL.md` step 8's unpushed-overlap check defines two branches:

- **Unattended** - take the genuinely-separate path, proceed, and record the overlap in the run's
  summary.
- **Interactive** - "STOP, name the overlapping commits and blamed lines, ask via
  `AskUserQuestion` whether to fold via `/commit fold <sha>` or state it and proceed."

`overlap-check.sh` exited 1 on **7 of the 10 commits**, every one against non-HEAD unpushed commits
(`d8086ef`, `e913ea7`, `56ad5cd`, `9ffcee2`, `bb65534`, `3ef4be0`, `5ec8cba`). That is not
anomalous, it is structural: a deep unpushed stack means almost any file you touch was already
touched by something in it. Obeying the interactive branch literally would have meant seven
`AskUserQuestion` cards, each asking Joe to adjudicate a fold against a commit from a session he
was not in, in the middle of an autopilot run he had asked to run unattended.

What actually happened: the run took the unattended branch's behaviour (proceed, disclose in the
summary) while interactive, and said so in the message. That was the right outcome and the wrong
process - the skill has no clause permitting it, so it was a deviation, not a documented path.

The friction is real but the current rule is not obviously wrong either: the check exists because a
silent overlap can bury another session's work. The gap is that its cost scales with unpushed depth
while its value does not.

## Approach

Options, roughly in increasing effort:

1. **Batch the question.** Collect overlaps across a multi-commit run and ask ONCE at the end
   ("these 7 commits overlapped older unpushed work, fold any?"), rather than gating each commit.
   Keeps the signal, drops the interruption.
2. **Scope the gate by authorship.** Only stop when a blamed sha was written by a DIFFERENT session
   - the risk the check exists for. An overlap with the dev's own earlier commits in the same
   local stack is the common, benign case. `overlap-check.sh` already resolves shas, so it could
   compare against this session's own commit list.
3. **Depth threshold.** Above N unpushed commits, fall through to the unattended behaviour
   automatically and say so once.
4. **Document the status quo.** Add an explicit clause that an interactive run may take the
   unattended branch when overlaps exceed some count, so a run doing the sensible thing is not
   deviating.

(2) is the one that actually targets the risk; (1) is the cheapest real improvement. They combine.

## Acceptance

- A 10-commit interactive session on a 20-deep unpushed branch produces at most one overlap
  question, or none when every overlap is against the session's own commits.
- The protection the check exists for still fires: an overlap with another session's unpushed
  commit still stops and asks.
- `skills/commit/SKILL.md` step 8 describes whatever behaviour is chosen, so no future run has to
  improvise.

## Notes

- Do not simply delete the interactive branch. The hunk-level upgrade behind it (todo 368) and the
  script (todo 474) were deliberate work; this is about when to ASK, not about whether to detect.
- Runtime is also worth a look while in here: `overlap-check.sh` scales with pathspec size times
  unpushed depth, and on this branch each call took several seconds.
