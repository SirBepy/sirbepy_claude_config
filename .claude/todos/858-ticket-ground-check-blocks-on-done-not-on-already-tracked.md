<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Checked against 800 (outbound marker vs sensitive-file-guard collision) and 831 (log.md append
     blocked by the permission classifier): both are about the ticket path's PLUMBING failing to
     run. This one is about the ground check running fine and returning the wrong verdict. Shared
     vocabulary only. -->
# /ticket's ground check blocks on already-DONE work but not on already-TRACKED work

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/ticket`'s create path treat an OPEN tracker hit that covers the same work as a reuse
candidate that must be put to the dev, instead of letting it pass as a "soft" signal and proceeding
straight to ticket-creation questions.

## Context

`refs/outbound-ground-check.md` query 2 searches the tracker, and its Verdict section lists exactly
one tracker-related hard stop: a hit already in a **done-equivalent state** (Shortcut `Done` or
`Testing`, Linear `completed`/`canceled`/`started`). Everything else is classed SOFT - "name it
inline in the draft and proceed".

That leaves a gap for the more common case: a hit that is OPEN and covers the same work. The
verdict for it is "proceed", so the create path runs on to `skills/ticket/SKILL.md`'s Create step 2
("Front-load the questions": title, epic, priority, estimate) and the dev is shown a creation card
for a ticket that should not exist.

Hit live in zng-app on 2026-09-01. A search returned **sc-54902 "UX: Design the service fee
discount UI for PRB/BRB users"** (`story_type: chore`, epic 54687, open, workflow_state 500000033).
It was reported to the dev, classed as design-only, and a new `FE:` sibling was drafted under it
with a full four-field question card. The dev's answer: *"but you just said you found the ticket,
lets just reuse the ticket you found"*. No ticket was filed; the work went onto sc-54902 as a commit
prefix plus one comment.

Note the shape - the hit was a `UX:` design ticket and the new work was FE, which is exactly the
distinction that made "these are different units of work" feel defensible. It wasn't.

## Approach

In `refs/outbound-ground-check.md`, add a third verdict between SOFT and HARD STOP - call it
**REUSE CANDIDATE** - for a query-2 hit that is open AND whose scope overlaps the draft's. Its
treatment: do not write the marker yet, do not ask the creation questions, put the hit to the dev
first with the story id, title, type and state, plus a one-line reason the draft is or is not the
same unit of work. Creation proceeds only if the dev says it is genuinely separate.

In `skills/ticket/SKILL.md`'s Create section, reorder so the ground check (step 3) runs BEFORE the
front-loaded creation questions (step 2). Asking title/epic/priority/estimate before the duplicate
gate has run is what turns a reuse into a filed ticket. State explicitly that a `UX:`/design-typed
hit is NOT automatically a different unit of work from its implementation.

## Acceptance

- `refs/outbound-ground-check.md` documents the REUSE CANDIDATE verdict, when it fires, and that no
  marker is written while it is unresolved.
- `skills/ticket/SKILL.md`'s Create steps are ordered ground-check-then-questions, and say a design
  ticket can be the reuse target for FE work.
- Re-running the sc-54902 scenario (search surfaces one open UX ticket covering the draft's scope)
  reaches a "reuse sc-54902?" question, not a title/epic/priority/estimate card.
