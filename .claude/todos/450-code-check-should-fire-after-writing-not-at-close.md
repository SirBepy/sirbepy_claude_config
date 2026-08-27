<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=HARD, worth=5, reconfirm-count=1, content-hash=ffbd0b07 -->
<!-- duplicate-checked -->
# /code-check should fire right after code is written, not only at /close

**Type:** skill-improvement
**Origin:** dev

> **SPLIT 2026-08-22 by Joe. Half of this shipped; what remains is the TRIGGER only, and it is
> sequenced behind todo 427 in phase 6. Read "Status" at the bottom before doing anything.**

## Goal

Give `/code-check` an automatic post-write trigger, so the review fires when code is written
rather than only when a session reaches `/close`, and remove the `/close` call once that lands.

The fresh-subagent half of this todo is DONE and is no longer in scope here.

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

## Status 2026-08-22 - split in two, half shipped

**Shipped: the fresh-reviewer property.** `/code-check` now dispatches its own analysis into a
subagent, in a new "The analysis runs in a fresh subagent, always" section at the top of
`skills/code-check/SKILL.md`. The invoking session resolves scope, dispatches, and writes the todo
files (the backlog contract forbids a subagent doing that); the subagent runs Steps 0-4 read-only
and returns findings. The dispatch may carry the scope, the file list and the diff, and may never
carry what the session was trying to do. `skills/close/SKILL.md:149` now says so at the call site,
and there is a stated `isolation: NOT held` fallback for runners with the Agent tool disabled
(pre-empting todo 483 for this one skill).

**Why that half became urgent.** This todo assumed the fresh-subagent property was a property of
firing EARLIER. It is not, and worse, it was not held anywhere: `skills/close/SKILL.md:149`
invoked `/code-check` **via the Skill tool, in the authoring session**, and `CLAUDE.md:27` records
that subagents cannot invoke skills at all. So the review has been running inside the session that
wrote the code this whole time, which is the exact thing this todo objects to, live and unnoticed.
Fixing it needed no hook, no `settings.json` and no dependency on 427.

**Deferred: the trigger, and it stays deferred.** A `Stop`-hook design was written and rated at a
median **3/10** by a 3-lens `/rate-it` panel plus an adversarial verifier. Confirmed flaws, each
checked against the files:

- A `Stop` hook's `{"decision": "block"}` (the live pattern at `hooks/ui-screenshot-reminder.py:110`)
  only re-injects text into the SAME session that wrote the code. It cannot make anything
  structural, so it fails this todo's own Approach step 3.
- `/close` Phase 2 already has a tuned size floor (`skills/close/SKILL.md:130`: skip under 50 added
  lines, with a written rationale). The proposed trigger discarded it and reinvented a cruder one.
- `ui-screenshot-reminder.py`'s sentinel is a single boolean, fired once per session
  (`:96`). The per-file freshness set this trigger needs is new state, not reuse.
- Six `Stop` hook blocks are already wired and three of them can emit `decision: block`. A fourth
  stacking on the same turn is untested.
- Todo **427 is still open** and is building the source-file-edited signal. Building a second one
  here is what this todo's own last line warns against.

One structural alternative was found and rejected on cost, not principle: the hook could spawn its
own `claude -p` reviewer, which `tools/skill_eval.py` already proves works here (fresh process,
`--disallowed-tools`, `subprocess.run`). That harness runs on a 300s timeout at roughly $0.20 a
call, against a repo where every wired `Stop` hook is capped at 15 to 30 seconds. Worth
reconsidering only if 427 lands and the signal turns out to be the only missing piece.

**One rater claim was refuted** and should not be recycled: that firing more often would multiply
the false positives in todos 471 and 456. Those are `/commit`'s regex prefilters
(`skills/commit/prefilter-gate.sh`), structurally unrelated to `/code-check`.

**The cost figure is still unmeasured.** An earlier estimate of ~60.8k tokens per dispatch came
from rating subagents, not a `/code-check` dispatch, and does not transfer; the standing note for
a general-purpose subagent is 15-20k. Whoever builds the trigger owes a real measurement, per this
todo's own Acceptance.
