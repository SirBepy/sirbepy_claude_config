<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=7, reconfirm-count=2, content-hash=ef757c18 -->
# Nothing tells a session to pull a ticket's linked design before implementing it

**Type:** skill-improvement
**Origin:** ai

## Goal

When a session implements a ticket that descends from (or links to) a UX/design ticket with an approved Figma, some step should surface that Figma BEFORE code gets written - not leave it to be discovered after the fact, by accident, only because the dev happened to ask "is there an actual design we should have followed?"

## Context

zng-admin session, 2026-08-25. Built sc-55166 (FE implementation split off sc-54515, a UX ticket) entirely from the prose spec in sc-54515's description - character key, warnings, copy. Never pulled sc-54515's linked Figma (`external_links` on the story, plus a more specific frame linked in a comment) before or during implementation. The actual approved design turned out to be a full dedicated page with a different information architecture (always-visible sidebar key, per-character preview chips, example-autofill, table-style masks list) than what got built (an inline-expand row matching the app's existing compact pattern). The divergence was real and load-bearing enough that the dev asked to see the design and weigh in on which UX to keep - caught only because he asked, not because any skill step surfaced it.

`skills/ticket/SKILL.md`'s Create flow already has a relevant precedent for the read side ("Ground the draft in current code first... Never paraphrase a linked design ticket's spec text as if it were that diff") but that's about drafting a TICKET, not implementing one. Pickup mode reads "current state, blocked/blocker relationships, and any linked branches, PRs or commits" but doesn't call out design links (Figma URLs in `external_links` or in comments) as something to fetch and read alongside the prose.

## Approach

Add an explicit step somewhere in the implementation path - candidates, pick whichever fits without duplicating: `/ticket`'s Pickup flow (fetch + skim any linked Figma alongside comments, before summarizing/handing off), `/brainstorm`'s pre-work checklist (before implementing a ticket, check for a linked design and pull it, not just read the prose spec), or a general CLAUDE.md Execution Discipline bullet ("a ticket descending from a UX ticket with a linked Figma: pull the Figma before writing code, don't implement from prose alone"). `reference_figma_access.md`-style recipes already exist per-project for the mechanics; this is about the missing trigger to use them.

## Acceptance

- A ticket-implementation flow that encounters a linked Figma (on the ticket itself, or on a ticket it descends from / relates to) surfaces it to the session before code gets written, not after.
- Doesn't fire on tickets with no design link (most bug/chore tickets) - scoped to UX-descended feature work.

## Notes

- Completed in wave 2, commit a851249: the /ticket Pickup flow now pulls a linked design before implementing a UX-descended ticket, reusing the shape the Create-flow ground check already had.
