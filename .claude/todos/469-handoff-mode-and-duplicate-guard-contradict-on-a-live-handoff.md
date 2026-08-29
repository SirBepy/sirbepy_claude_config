<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=7, reconfirm-count=1, content-hash=51eabc82 -->
<!-- duplicate-checked -->
# ai-todos-format contradicts itself when a handoff is written and a live handoff already covers it

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `~/.claude/skills/close/ai-todos-format.md` say one thing about writing a second handoff for
work a live handoff already covers, so a cold session does not have to adjudicate two of its rules
against each other mid-write.

## Context

Two sections of the same file give opposite instructions for the same situation.

**Content-duplicate guard** says every writer, `/handoff` named explicitly among them, must grep
the destination first and resolve a hit to one of three outcomes, the first being:

> Destination has a LIVE todo for it: fold in, do not create a second file.

**Handoff mode**, further down, says:

> A handoff never edits, replaces, or deletes a prior handoff todo - each call writes a new file
> with a fresh id and a new PLAN.md line; old handoffs stay as history.

Hit directly on 2026-08-21 in revaire-mobile. `/handoff` was invoked while
`51-handoff-rev-4810-review-and-ship.md` was live and covered the same branch and the same ticket.
The guard said fold into 51; handoff mode said write 52. Resolved by treating handoff mode as the
more specific rule and writing `52-...`, marking it as superseding 51 in its own body and adding
`<!-- duplicate-checked -->` so `hooks/todo-duplicate-guard.py` would not block. That is a
defensible reading, but it is a reading, and the other reading loses session history by folding a
current handoff into a stale one.

The stakes are asymmetric and that is the argument for stacking: a stale handoff folded into is
unrecoverable, a redundant handoff is just noise `/cleanup-todos` can bin later.

Related but distinct, do not fold into either: `457-merge-several-sessions-into-one-via-handoffs.md`
is about the READ side (one `/pickup` consuming N handoffs); this is the WRITE side.
`done/363-content-duplicate-guard-has-no-enforcement.md` built the backstop hook and did not touch
the handoff exemption.

## Approach

Cheapest fix, in `ai-todos-format.md`'s Content-duplicate guard section: add handoffs as a named
fourth outcome rather than leaving handoff mode to override by implication.

> **Handoffs are exempt from fold-in.** A handoff whose subject matches a live handoff is still
> written as a new file with a fresh id - see Handoff mode. Reference the prior handoff's id in
> the new file and state which of its facts are now superseded; never edit or delete the old one.

Then, in Handoff mode, add the reciprocal half-sentence so each section points at the other, and
say the new file should carry `<!-- duplicate-checked -->` since it will predictably trip the hook.

Worth deciding at the same time and writing down either way: whether the superseded handoff's
PLAN.md line stays (it was kept on 2026-08-21, annotated "superseded by 52, kept as history") or
is removed so the lane shows one baton. Ambiguous today; the file should just say.

## Acceptance

- Both sections cross-reference each other; neither can be read alone and produce the wrong action.
- The PLAN.md question for a superseded handoff has a stated answer.
- A cold session given "a live handoff exists for this branch, /handoff was invoked" reaches the
  right action from the file alone, with no adjudication.
