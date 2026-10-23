<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# /ticket + outbound verifiers: every requirement in a ticket must cite a product source

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop Claude from filing tickets at other engineers whose action items or acceptance criteria go beyond what the product/design source says. Surfaced in a zng-biller session on 2026-10-22.

## Context

- zng-biller, Shortcut sc-56481 "BE: Block removing or demoting the last Biller Admin of a biller group", filed 2026-10-22 09:00 UTC under Joe's account by a Claude session.
- Source: UX sc-56277 (Airion, product owner) says "Ensure at least one Admin must remain on the account at all times"; the Figma says "the last Admin cannot be demoted or removed". Both are about portal team management.
- The ticket's action item and AC said "reject ... for every caller including `admin`" (Zirtue staff) and added guards on user delete/archive routes. No source said that.
- The BE dev (Stevan) objected on the ticket: removing all biller admins is a valid offboarding case. On re-read, existing BE rules already met the portal rule (`DELETE users/:id/roles` is Admin/BillerAdmin/PartnerAdmin-only and rejects self-removal; sc-56476 blocks self role change), so the ticket was unnecessary.
- Joe: "Im rly embarassed ... This was very bad for my image".
- The 3-verifier outbound guard passed the ticket: verifiers check that code facts are true, not that each requirement traces to a source or is needed at all.

## Approach

- `skills/ticket/SKILL.md` Create flow: before drafting, list each requirement with its source (ticket line, Figma text, dev's words). Unsourced items go under a "Questions" heading marked as Claude's suggestion, never as action items or ACs.
- Same step: for "the BE lacks guard X" tickets, check whether existing constraints (role guards, self-action blocks, other open tickets) already make the forbidden state unreachable for the actors the rule covers, and ask who legitimately needs the blocked action (staff, support, offboarding).
- `refs/outbound-verify.md`: add a verifier check, "every action item and AC traces to a cited source; flag any that widen it (more callers, routes, actors)".

## Acceptance

- A cold session filing a BE ticket from a UX rule produces ACs that each name a source, and widened scope appears only as a question.
- The verifier prompt template fails a ticket with an unsourced AC.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): ticket Create step 5 sources every requirement (unsourced go under Questions) and checks a 'BE lacks guard X' premise against existing guards and legitimate actors; outbound-verify template step 4 Source trace FAILs unsourced or widened items. Hook tests ALL PASS.
