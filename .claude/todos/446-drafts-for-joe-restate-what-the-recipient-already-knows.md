<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# Drafts for Joe to send restate what the recipient already knows

**Type:** skill-improvement
**Origin:** dev

## Goal

Make Claude select a colleague-message draft's CONTENT by what the recipient needs, not by what
Claude happens to have in context. Today the drafts are correctly shaped (short, lowercase, casual)
but carry facts the reader already knows or has no use for.

## DISCUSS FIRST - do not execute

Joe wants to talk this over with someone on the Revaire side before any of it is built. Filing it
is the whole job for now. A future session that picks this up should confirm with Joe that the
conversation happened and what came out of it, rather than implementing the Approach below as
written.

## Context

Surfaced 2026-08-20 in the revaire-mobile `rev-5312` session. Bruno sent Joe a review note saying
the environment picker should check the returned `200008` code rather than rely on the pinned build
existing. Claude fixed it, then drafted a reply that explained the fix back to Bruno, including a
file path - to the person who had just specified that exact fix. Joe's own rewrite was
`Whoops ye mb, fixed it now`, which is the correct length and content.

Joe's framing, verbatim: "you often want me to write stuff the other person already knows / or the
other person never needs to know (like explaining code to a designer...)".

Two existing rules touch this and neither prevents it:

- The `feedback_colleague_message_drafts` memory (revaire-mobile scope) fixes FORM only: 1-3 casual
  lowercase lines, no bullets/headers/bolding. A draft can obey it perfectly and still be all noise.
- Global `CLAUDE.md`'s outbound bullet says every factual statement and number in a draft "either
  carries a receipt or gets cut". This actively pushes the wrong way: Claude keeps resolving the
  either/or by CITING when the right answer is usually CUTTING. The rule exists to stop invented
  facts, not to require that true ones be included, but nothing in the wording says so.

The missing step is a recipient model. Three questions per sentence:

1. Did they already tell me this? (Bruno specified the fix; restating it is pure noise.)
2. Can they act on it or decide with it? If not, cut.
3. Is it in their domain? (A designer fails this on every implementation detail - file paths,
   function names, test counts.)

## Approach

Joe's stated preference, in his words: "makes more sense to add a skill to me, and myb a stop hook
on top if it doesnt waste tokens". His objection to a hook as the primary mechanism: "stop hook
means that we are only fixing after we wrote it".

So the shape to bring to the discussion, not to build unilaterally:

1. **A skill as the primary mechanism.** Model-invocable, firing on "reply for X", "what do I tell
   X", "draft a message to X". It runs BEFORE drafting, which is the half a Stop hook cannot do.
   Contents worth sketching: name the recipient and their role, state in one line what they already
   know (especially anything they themselves said in the thread being answered), then draft only
   the remainder. Default 1-3 lines; if the draft exceeds it, cut content rather than compress
   wording.
2. **Optionally a Stop hook on top**, gated on Joe's token concern. The trigger is mechanically
   cheap: drafts for Joe to send are always blockquoted per the copy-paste rule in
   `refs/copy-paste-format.md`, so a hook can detect a blockquote in the turn and inject the three
   questions. Same shape as the existing `ui-screenshot-reminder`, which demonstrably changed a
   turn in this very session. It catches drafts the skill never fired on, and it fires before Joe
   pastes, so "only fixing after we wrote it" is half true - the message has been written but not
   sent.
3. **Amend the outbound bullet in global `CLAUDE.md`** so the receipts rule cannot be read as a
   requirement to include evidence: receipts gate what MAY be said, they never oblige saying it.
   Worth doing regardless of 1 and 2, and cheap.

Rejected: a prose-only fix (option 3 alone). `CLAUDE.md` itself warns that a wording-only fix
already failed for this class of rule, citing the em-dash enforcement history.

Related but distinct, do not fold together: [[435-prose-enforcement-is-one-hardcoded-character-ban]]
covers AI-flavoured writing TELLS (voice, punctuation, style profile). This todo is about content
SELECTION for a specific reader. A draft can pass 435 and still fail this one.

## Acceptance

- A reply drafted for someone who supplied the fix does not restate the fix.
- A message drafted for a non-engineer carries no file paths, symbol names, or test counts.
- The form rules still hold: 1-3 casual lowercase lines, no bullets or headers.
- Whatever gets built does not fire on Claude's own chat replies to Joe, which are a different
  surface with different rules (`snippets/terse-replies.md`).

## Notes

- Joe has not approved building anything yet. The discussion gates all three items above.
- If the discussion lands on the skill, check whether it should absorb the revaire-mobile
  `feedback_colleague_message_drafts` memory's form rules so the two do not drift.
