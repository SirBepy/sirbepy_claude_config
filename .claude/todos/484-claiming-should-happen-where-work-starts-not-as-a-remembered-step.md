<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=2, content-hash=c99b377f -->
<!-- duplicate-checked -->
<!-- Todo 328 is DONE - it shipped the non-blocking warning. Its own Notes scoped the fix below
     OUT as "a much bigger change". This is that deferred follow-up, with fresh evidence that the
     warning alone does not work. -->
# Claiming should happen where work starts, not as a step every runner has to remember

**Type:** skill-improvement
**Origin:** ai

## Goal

Move the claim from "an instruction the model must remember" to "something the tooling does when
work begins", so the non-negotiable claim rule stops depending on recall inside a batched run.

## Context

Todo 328 (DONE, 2026-08-15) added the non-blocking warning `complete-todo.ps1` prints when a todo
is completed with no claim on record. Its Notes deferred the real fix:

> The deeper fix would be for whatever executes a todo to claim it automatically, but that is a
> much bigger change across `/pickup`, `/batch-todos`, autopilot and ad-hoc runs. The warning is
> the cheap detection layer that makes the bigger fix's absence visible in the meantime.

**2026-08-22, `hubbub-game-split-opinions`: the detection layer works, and it is not enough.** A
two-round `/auto-do-todos` session completed FOUR todos with no claim on record - 04, 05, 10 and
12. The warning fired correctly all four times, buried in a wall of other script output, and the
run continued past every one. So the cheap layer did its job and the job is insufficient: a
non-blocking warning inside a batched run is indistinguishable from noise.

The pattern in the four misses is the useful part. Every one was a todo handled *alongside*
another:

- 04 rode along with 03's edit and commit (one logical change, two todo ids)
- 05 and 12 were archived together on a direct instruction from Joe
- 10 was closed on a verdict, with no code written at all

Claiming is a separate remembered tool call, so it gets skipped exactly when several todos move at
once - which is also the moment a concurrent session is most likely to collide. That is not
hypothetical in this estate: the same session had a second Conductor session commit into the same
repo mid-run (`a53c546`) and file its own todo (15), minutes after `list_peers` had reported no
peers.

## Approach

The unit of enforcement should be "work started on id N", not "the model remembered to run a
script". Options, roughly cheapest first:

1. **Claim inside the completion helper's sibling.** Have `/auto-do-todos` Step 6, `/batch-todos`,
   and `/pickup` call `claim-todo.ps1` as part of the *same* tool call that begins the todo's work,
   never as a preceding standalone step. Prompt-level only, so it can still be skipped - but it
   removes the separate-call failure mode that produced all four misses above.
2. **Claim-on-first-write.** A `PreToolUse` hook on `Edit`/`Write` that maps the touched paths to
   an in-flight todo and auto-claims. Strongest, and the only option that cannot be forgotten, but
   needs a reliable path-to-todo mapping that does not exist today.
3. **Batch claim.** A `claim-todo.ps1 -Id 03,04,05` form so handling several todos at once is one
   call rather than N remembered ones. Cheap, and directly targets the observed pattern.
4. **Accept and narrow the rule.** If a claim genuinely only matters for todos that involve real
   execution time, say so in `CLAUDE.md` instead of "every path", and stop warning on verdict-only
   closes and instructed archivals - two of the four misses above were exactly those.

Option 3 plus option 1 is probably the best effort-to-value trade. Option 4 is worth considering
seriously rather than dismissing: two of the four "violations" were arguably not violations at all,
and a rule that fires false positives half the time is training the model to ignore it.

Files: `~/.claude/skills/close/claim-todo.ps1`, `~/.claude/skills/close/ai-todos-format.md`,
`~/.claude/skills/auto-do-todos/SKILL.md`, `~/.claude/skills/batch-todos/SKILL.md`,
`~/.claude/skills/pickup/SKILL.md`, global `CLAUDE.md`'s AI todos section.

## Acceptance

- Handling N todos in one batch takes no more remembered claim calls than handling one does.
- A run that completes a todo unclaimed either cannot happen, or is a case `CLAUDE.md` explicitly
  says does not need a claim.
- `ai-todos-format.md` and `CLAUDE.md` agree with whatever the scripts now do.
