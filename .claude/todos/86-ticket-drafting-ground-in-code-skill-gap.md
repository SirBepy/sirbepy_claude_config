<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=7, reconfirm-count=2, content-hash=4dc49929 -->
# Skill gap: no process for grounding FE implementation tickets in current code before drafting

**Type:** skill-improvement

## Goal

Close the gap that let this session draft two rounds of inaccurate ticket content before Joe had to explicitly say "look at what we currently have for [screen], see the diff to the new flow, and use that to create the ticket."

## Context

Session 2026-07-21: reviewed epic 54687 (Partner entity type work) and its 10 subtasks, then was asked to draft implementation tickets for the admin (zng-admin) FE work. Sequence of missteps before landing on the right approach:

1. Drafted 2 bug tickets in repro/actual/expected format from screenshots Joe pasted, before confirming whether they were live-product screenshots or Figma mockups. They were Figma mockups — wrong template entirely, no "actual behavior" to repro against a design.
2. Split into 2 tickets for symptoms that turned out to share one root cause/screen; Joe: "i think this could just be 1 ticket... no?"
3. Mislabeled the merged ticket as `UX:` type; Joe: "not ux... ux is for design... lets make a ticket for the admin" — needed an FE/build ticket, not a design ticket.
4. Drafted the FE implementation ticket by paraphrasing the *linked design tickets'* spec text (54704/54708/54711) rather than reading the actual current zng-admin code. Joe, sharply: "bro... idk whats up with you, this is pretty bad... look at what we currently have for biller group page, and see what the difference between that flow is and the new flow." Only after dispatching an Explore subagent to read `biller_groups_screen.dart`, `create_biller_group_screen.dart`, `biller_group_details_screen.dart` etc. and diffing that against the design spec did the ticket land correctly.

None of the active skills (`shortcut-create-ticket`, `create-todo`) instruct drafting FE tickets to start from a read of the actual current implementation. `shortcut-create-ticket` only covers mechanical creation (defaults, custom fields, dup-check) once content is already decided — it doesn't cover the upstream judgment call of *how* to arrive at accurate ticket content for "implement X" style FE tickets.

## Approach

Consider adding a short section to `shortcut-create-ticket` (or a new pre-step it references) covering FE "implement this design/flow" tickets specifically:

- Before drafting scope/description for any ticket that says "implement X flow" or "build Y screen": if a codebase exists for the affected app, read the current implementation of the affected screen/flow first (not just the linked design ticket's spec text) and diff against the new design. Ground the ticket in that diff.
- Confirm whether visual references (screenshots) are live-product or design-tool (Figma/Miro) mockups before choosing a ticket template — repro/actual/expected only applies to a defect in a *running* product.
- Default to one ticket per shared root-cause/screen rather than one ticket per symptom found on that screen, unless the dev says otherwise.
- Ticket description length should scale to audience: full written scope only for cold-pickup-by-a-stranger tickets; short (what changed + design link + 1-line key behavior) when the dev is implementing it themselves and the ticket exists mainly for the tester to verify against.

Do not draft the skill edit inline — this todo is the candidate, not the fix.

## Acceptance

- Next session drafting an "implement X" FE ticket reads the current code for the affected screen/flow before writing ticket content, without the dev having to ask for it.
- Ticket template choice (bug repro vs plain description) correctly follows from whether the reference material is live product or design-tool output.

## Notes

The eventual fix landed well once corrected — the Explore-subagent-diff-against-code approach worked cleanly for both `sc-54839` and `sc-54840`. The gap is entirely about *defaulting* to that approach without being told, not about capability.
