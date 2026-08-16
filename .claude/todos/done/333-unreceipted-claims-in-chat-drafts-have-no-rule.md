<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-15, complexity=HARD, worth=6, reconfirm-count=1, content-hash=869b10db -->
# Chat/Slack drafts Claude hands the dev have no receipt rule, and no chokepoint to enforce one

**Type:** rule-improvement
**Origin:** ai

## Goal

Give outbound *chat* content the same "don't assert what you didn't check" discipline that
`shortcut-create-ticket`'s ground check now gives outbound *tickets*.

## Context

On 2026-08-14 a ticket was filed for work that was already done and the dev looked stupid in front
of his team. The fix that shipped that day covers ticket creation only: `ground-check.md` plus
`hooks/shortcut-create-guard.py`, which blocks the create POST unless the ground check wrote a
marker.

The dev's original complaint named messages first: *"i hate when AI tells me to make a ticket, or
write a msg or smth, and it turns out, it didnt do enough research"*. Chat is deliberately out of
scope for that fix, because there is no tool call to intercept - a Slack message the dev pastes by
hand touches nothing the harness can hook. This todo is that gap, filed rather than bolted onto a
ticket-creation change.

An `/iterate-it` run (5 rounds, converged 8/10) produced the rule text but dropped it from the
shipped change to avoid bloating `CLAUDE.md` the day before a full skill audit:

- A statement is receipted or it is cut. A receipt is a `file:line` read this session, a command's
  stdout, an API response, or a fetched URL. "I read it earlier" from a past session is not one.
- Every number is receipted or cut. No estimated percentages, counts, or durations.
- Certainty language must match the evidence. "is/does/will" needs a receipt.
- Never draft a reply to a thread you were not given in full. Ask for the thread instead.

`CLAUDE.md`'s Execution Discipline section already carries an adjacent rule (the UNVERIFIED
labelling requirement) which notes it *"recurred 5 times in one project despite being
memory-documented after each one; a wording-only fix already failed once for this exact class of
rule"*. That is the prior to beat: adding four more lines of prose may not change behaviour.

## Approach

Decide between two shapes, and do NOT default to the prose one just because it is cheaper:

1. **Extend the existing UNVERIFIED rule** in `CLAUDE.md` Execution Discipline with an explicit
   outbound-artifact clause, rather than adding a new section. Cheapest, and it lands where the
   related rule already is, but it inherits that rule's demonstrated failure rate.
2. **A UserPromptSubmit hook** that injects the rules when the prompt reads as an outbound request
   in a work repo ("make a ticket", "draft a message", "reply to", "what should I tell", "write the
   standup"). Non-blocking, so its failure mode is a missed prime, never a false block. Roughly 200
   tokens per triggering prompt. The phrase list will be wrong at first and needs appending to as
   real misses show up.

Whichever ships, work-vs-personal scoping needs a `project_kind()` helper (marker file, else origin
remote owner in `zirtue-corp`/`Fibo-Studio`/`revaire`, else personal). Note that
`gh-account-switch.sh` already holds that org mapping in bash, so a Python copy needs a parity test,
not a "keep in sync" comment.

## Acceptance

- An outbound chat draft in a work repo either carries receipts for its factual claims, or those
  claims are cut or turned into questions.
- Personal projects are unaffected.
- If the hook route is taken, a missed prime never blocks a turn.

## Notes

- Filed 2026-08-14 alongside the ticket-side fix, which is the other half of the same problem.
- Related: [[326-replicate-ui-verification-hook-to-zng-siblings]] for the hook-replication pattern.
- Three of four `EXPERIMENTAL-` spikes in `~/.claude/hooks/` were never promoted to blocking. If
  this becomes a hook, it should be non-blocking by design rather than a spike awaiting promotion.
- Done 2026-08-16. Joe chose the prose route with one scope for all outbound chat, not a hook and not a work/personal split. CLAUDE.md Execution Discipline now extends the UNVERIFIED rule to outbound drafts Joe sends as his own words: receipts or cut, certainty language needs a receipt, never draft a reply to a thread not given in full.

## Open questions

Written by /auto-do-todos on 2026-08-15. The next run opens with these.

- [ ] [ARCH] The todo names an undecided fork and it is the whole job. Options: extend the existing
      prose rule in `CLAUDE.md`'s Execution Discipline (which today covers claims about systems not
      read this session, a narrower scope than outbound chat receipts) / build a `UserPromptSubmit`
      hook / do nothing until a chat-side incident actually happens. Recommended: **extend the prose
      rule**. A detector for "did this claim get checked" is a judgment call, and this repo's hook
      doctrine has already killed three of those; the cited incident was ticket-side and is already
      fixed by `a7c09a6`, so the chat half has no incident of its own yet.
- [ ] [TOOLING] If the prose route wins, does it need a work-versus-personal scope split, per the
      todo's own aside? Options: one rule for all outbound chat / stricter for client-facing (Slack,
      Shortcut comments) than for personal. Recommended: **one rule**, because a split needs a
      reliable signal for which channel a draft is headed to, and there isn't one.
