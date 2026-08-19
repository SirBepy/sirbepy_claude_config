<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Builder dispatches must demand real-input verification for interaction features

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop accepting subagent reports whose verification method cannot, even in principle, prove the
feature works. Specifically: synthetic DOM events passing while the real interaction is broken.

## Context

2026-08-16, honeymoon-tools session. A builder implemented drag-to-reorder in a shortlist table
and verified it by dispatching synthetic `dragstart` / `dragover` / `drop` events. Every check
passed and the report read as strong evidence. **The feature did not work at all for a real user**
and Joe reported it two dispatches later.

Root cause of the underlying bug is exactly what makes synthetic verification useless here: per
the HTML5 drag spec, when the draggable element is an ancestor (`<tr draggable>`) and the pointer
lands on a child (`.drag-handle`), the browser fires `dragstart` with `e.target` set to the DRAG
SOURCE, not the child. The code guarded on `e.target.closest('.drag-handle')`, which can never be
true for a real mouse. A dispatched event sets `target` to whatever the test chooses, so the guard
passed in the test and failed in reality.

The re-dispatch that fixed it was told to use Playwright's real mouse API
(`mouse.move` / `mouse.down` / incremental `mouse.move` / `mouse.up`) and found the cause in one
pass.

This is a general class, not a drag-specific quirk. Any feature whose behaviour depends on real
browser input plumbing (drag and drop, focus and blur ordering, pointer capture, native scroll,
IME, paste, keyboard activation of links) can pass a `dispatchEvent` test while being broken.

Relevant files:
- `~/.claude/refs/delegation-doctrine.md` - "Visual work" section already says a green verify floor
  is not enough for visual work and demands a rendered artifact. It does not cover interaction.
- Same file, "Quality tells (when to distrust a report)" - lists suspiciously clean, contradicted,
  and vague. It does not list "verified by a method that cannot fail".

## Approach

Add to `~/.claude/refs/delegation-doctrine.md`, most naturally as a sibling of the existing
"Visual work" section (call it "Interaction work"):

- When a dispatch implements behaviour that depends on real browser input, the verify floor must
  use real input APIs, not `dispatchEvent`. Name the concrete ones: Playwright `page.mouse.*`,
  `page.keyboard.*`, `locator.dragTo()`, real `focus()` plus typing rather than setting `.value`.
- State the reason inline so it is not read as ceremony: a synthetic event lets the test author
  choose `target`, `isTrusted`, and the event sequence, which are precisely the things the real
  browser decides and the bug usually lives in.
- Extend "Quality tells" with a fourth entry: **verified by a method that could not have failed**.
  Response is the same as the others, a targeted re-check, but the trigger is the METHOD rather
  than the result.

Rejected alternative: banning synthetic events outright. They are fine for unit-level logic and
for driving app state in a controlled way; the failure is using them as proof of an integration
that depends on browser plumbing.

## Acceptance

- `delegation-doctrine.md` names interaction work as a category needing real-input verification,
  with concrete API names.
- "Quality tells" lists the could-not-have-failed method as a distrust trigger.
- The wording is specific enough that a builder writing its own verify plan would pick the real
  API without further prompting.
- Does not regress the existing "Visual work" rule or the canonical builder preamble.

## Notes

Worth noting the near miss: the same session ALSO caught a real bug (missing hotels) because the
main agent refused to accept its own leading hypothesis without evidence, and the dispatched scout
disproved it. The discipline works when applied; this todo is about the one place it was not.
