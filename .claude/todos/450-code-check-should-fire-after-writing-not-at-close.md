<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# /code-check should fire right after code is written, always in a fresh subagent

**Type:** skill-improvement
**Origin:** dev

## Goal

Move `/code-check` from a `/close`-time sweep to an automatic post-write pass that always runs in a
fresh subagent, and remove it from `/close` once that lands.

## Context

Joe's own proposal, 2026-08-20, in response to the harvest report observing that `/code-check` only
reviews after the fact.

His reasoning for the current design, which is the part worth preserving: **AI is very bad at
reviewing its own code.** `/code-check` running later, separately, was a deliberate workaround for
that, not an oversight. So the fix is not "review earlier in the same context" - that would make it
worse. It is "review immediately, but always from a context that did not write the code."

A fresh subagent gives exactly that property for free: it has no memory of the authoring decisions, no
investment in the approach, and no recollection of what it meant to do. That is the same reasoning
Anthropic's documented Writer/Reviewer pattern rests on, and the same reason
`refs/delegation-doctrine.md` already treats a suspiciously clean self-report as a quality tell.

Current state: `/code-check` is callable standalone or from `/close`. Its findings go to the todos
backlog. Being at `/close` means the review happens at session end, potentially long after the code
was written, batched across everything the session did, and only if the session reaches `/close` at
all.

**Companion problem, filed separately as todo 451:** Joe does not read the code, so refactor findings
that land in the backlog are never requested. Moving the review earlier does not fix that. Both todos
are needed for either to matter, and 451 is the more important of the two.

## Approach

1. Read `skills/code-check/SKILL.md` and `skills/close/SKILL.md` to find the current call site and
   what `/close` passes it.
2. Decide the trigger, and be honest that this is the hard part. Options, in rough order of
   robustness:
   - A `Stop` hook that fires the review when source files were edited this turn. Most reliable, and
     todo 427 is already building the "source files were edited" flag-file signal, so **check whether
     427 has landed and reuse its signal rather than building a second one.**
   - A `PostToolUse` hook on Edit/Write that sets a flag, with the review dispatched at turn end.
   - A rule in CLAUDE.md. Cheapest, and the least likely to actually fire, per this repo's own
     repeated evidence about prose-only rules.
3. Make the fresh-subagent property structural, not advisory. The dispatch must go out as a real
   subagent with the diff as its input, and it must NOT be handed the authoring session's reasoning.
   Passing "here is what I was trying to do" reintroduces exactly the bias this whole change exists to
   remove.
4. Handle the noise question before wiring it, since a review on every code-touching turn is a lot of
   reviews. Decide what makes a turn worth reviewing (a size threshold, source-file-only, first turn
   touching a given file) and state the rule. A review that fires on every one-line edit will be
   ignored, which is the failure mode todo 440 also warns about.
5. Remove the `/close` call once the automatic path is proven to fire. **Not before.** Removing it
   first leaves a window with no review at all.
6. Check the cost. Each review is a subagent dispatch, so this is a real per-turn token cost on
   sonnet. Report the rough cost so Joe can judge whether the trigger is tuned right.

## Acceptance

- The review fires automatically after a code-writing turn, demonstrated on a real turn.
- It runs in a subagent that provably did not write the code (inspect the dispatch prompt: it carries
  the diff, not the authoring rationale).
- A prose-only or config-only turn does NOT trigger it.
- `/close` no longer calls `/code-check`, and that removal happened after the automatic path was
  verified, not before.
- The per-turn token cost is measured and reported.

## Notes

Do not "improve" this by having the authoring session review its own diff before dispatching. The
whole premise, in Joe's words, is that AI is very bad at reviewing its own code.

Sequence after todo 427 if possible, so the source-file-edited signal is built once rather than twice.
