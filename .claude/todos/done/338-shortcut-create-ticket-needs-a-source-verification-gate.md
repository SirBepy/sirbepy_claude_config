<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=EASY, worth=1, reconfirm-count=1, content-hash=0bc27c19 -->
# /shortcut-create-ticket needs a source-verification gate before filing at another engineer

**Type:** skill-improvement
**Origin:** dev

## Goal

Stop `/shortcut-create-ticket` from filing a ticket whose central factual claim was never checked
against the system it describes. Joe asked for this directly on 2026-08-14: "there needs to be more
rules setup before we go out and make tickets for other ppl".

## Context

On 2026-08-14 in `zng-biller`, a session filed **sc-55124** at Stevan (BE) asking him to add a
per-day registrations and payments series to `POST billers/dashboard`. The registrations half was
false. `BillerDashboardResponseDto` in `zng-api` had returned `registrationsCount` and
`registrations: DataPointResponseDto[]` since 2026-07-28 (commit `d950091a`). The claim came from
reading the *Flutter client's parser*, which hardcodes `registrationsLast30Days: const []`, and
inferring the server contract from it.

Stevan replied within the hour: "VeÄ‡ ti vraÄ‡am registracije po danu, to je dodato odavno." The
ticket went to Won't do the same day. Joe's reaction: "fucking hell man, what the fuck, there needs
to be more rules setup before we go out and make tickets for other ppl".

The skill file `~/.claude/skills/shortcut-create-ticket/SKILL.md` has a mandatory **duplicate**
check (step 2) and a "ground in current code first" step (step 0), but step 0 is explicitly scoped
to *FE "implement this design/flow" tickets* and says "skip for bugs, chores, or BE tickets". So a
BE ticket, the exact case where the filer is least likely to know the target system, has **no
verification requirement at all**. That is the gap.

Note there is a project memory covering the individual lesson
(`feedback_never_infer_api_shape_from_client_parser` in the zng-biller store), but a memory is a
per-project nudge, not an enforcement step in the skill every ticket passes through.

## Approach

Add a step to `SKILL.md`, sibling to the duplicate check and with the same MANDATORY framing, that
fires when the ticket will be **owned by someone other than Joe**:

1. Identify the ticket's central factual claim, the "X does not exist / does not work / is missing"
   assertion that justifies the ask.
2. Verify it in the owning system's own source, not in a client of it. For zng-api that means the
   controller and response DTO under `apps/core/src/modules/**`; the sibling repos are all local, so
   this costs one Read. CLAUDE.md's read-only carve-out means no fetch/pull ceremony is needed.
3. Record the verification in the ticket description or the skill's log entry: file path plus what
   was found. If it genuinely cannot be verified, the ticket must say "UNVERIFIED" in the text, or
   be sent as a question to the owning engineer instead of a ticket.

Consider a matching line in step 5's log template, e.g. `Verified: <file:line> - <what was found>`,
so the audit trail shows whether the gate ran.

## Acceptance

- `SKILL.md` carries a mandatory verification step for any ticket owned by someone other than Joe.
- The step names the concrete "read the server's own DTO, not the client's parser" failure mode,
  since that is the one that actually happened.
- The log template has a field proving the check ran.
- A dry read of the new step by a cold session would have caught sc-55124.

## Notes

- Do not fold this into step 0. Step 0 is about *design* fidelity for FE screens and explicitly
  exempts BE tickets; this is about *factual* claims and is needed most for BE tickets.
- Related, same session: the same wrong inference also reached a QA-facing comment on SC-54228 and
  had to be edited after posting. A verification gate on ticket creation would not have caught the
  comment. Worth considering whether `shortcut-update-ticket` needs the same gate.
- Archived 2026-08-16 as superseded, on Joe's word. Commit a7c09a6 shipped a strictly broader version the same day it was filed: a mandatory ground check for EVERY ticket, ground-check.md reading the owning system's source at the tracked branch, and hooks/shortcut-create-guard.py hard-blocking the create call without a fresh marker. The leftover shortcut-update-ticket gap moved to todo 351, which also carries Joe's unified /ticket idea.

## Open questions

Written by /auto-do-todos on 2026-08-15. The next run opens with these.

- [ ] [TOOLING] This todo's premise no longer holds. Commit `a7c09a6`, the same day it was filed,
      ships a strictly broader version of the ask: step 2 of `skills/shortcut-create-ticket/SKILL.md`
      is now a mandatory "Ground check" for EVERY ticket rather than only BE or other-owner ones;
      `ground-check.md` query 3 reads the owning system's own source at the tracked branch
      (`git show origin/<branch>:<path> | grep -n "<claim>"`), which is precisely the sc-55124
      failure mode; and `hooks/shortcut-create-guard.py` hard-blocks the create call without a fresh
      ground-check marker, which is stronger than this todo's "record verification or mark
      UNVERIFIED". Archive it, or keep it open? Options: archive to `done/` as superseded / keep it
      open for the `shortcut-update-ticket` half named in its own Notes / keep it open for another
      reason. Recommended: **archive**, and let the update-ticket gap be filed as its own todo,
      since that is a different skill with a different trigger. Archiving also resolves the id-338
      collision with the flutter-e2e todo. Dev-origin, so it waits on your word.
