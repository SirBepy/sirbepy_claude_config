<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped the backlog and done/ for contradict, override the ticket, reverses, instruction conflicts, ticket says, prior decision. Zero hits. The nearest existing rules are the CLAUDE.md "ground tickets in code" and "verify root cause first" lines, which govern Claude's own proposals, not an instruction from Joe that silently undoes one. -->
# 999 - Challenge an instruction that reverses a ticketed decision, before obeying it

**Type:** rule
**Origin:** dev
**Created:** 2026-09-23

## Goal

When Joe tells Claude to change something, and that something exists because a ticket, a ticket
comment or a recorded decision asked for it, Claude should say so and confirm before making the
change, rather than obeying and silently dropping the requirement.

Joe's own words, 2026-09-23: "we should honestly add a rule that whenever i tell you to do smth,
check if there was a good reason why you did it (like the ticket says to do it this way) and then
ask me if im sure i wanna ignore the ticket".

## Context

The incident that produced it, sc-55729 (desktop share sheet).

The ticket body lists two issues under Copy link. ISSUE 1 is the payload: Copy link copies the note
plus the link instead of the link alone. ISSUE 2 is the confirmation:

> The "Link copied" confirmation appears **inside the modal**, so a desktop user who is about to
> switch tabs may not see it.

The first fix, 92688f9, answered ISSUE 2 by no longer auto-closing the sheet, so the confirmation
stayed on screen until the user dismissed it.

Joe then told a different session not to keep the confirmation up. That session complied. The
landed commit, bea5f50, gives the copy buttons a two-second timer that reverts the label back to
"Copy link" and "Copy message & link". The sheet still stays open, but the confirmation itself is
gone two seconds after the copy, which is the opposite direction from the complaint the ticket
raised and never withdrew. Airion's later comment (2026-09-23 14:18) changed only which buttons
remain on desktop; it said nothing about the confirmation.

Joe realised it himself only afterwards: "oh i didnt realise he asked that the copied confirmation
must stay visible, i told another ai not to do that, whoops". By then bea5f50 was pushed to
origin/develop.

Why a rule rather than a one-off correction:

- The instruction was perfectly reasonable on its face. Nothing about "don't keep the confirmation
  up" signals that a ticket requirement is attached to it.
- The requirement lived one level down, in the ticket body's ISSUE 2, not in the code, not in the
  commit message, and not in the conversation. A session acting on the instruction alone would
  never see it.
- The loss is silent. No test failed, no reviewer objected, and the ticket looks satisfied because
  the visible half of the ask (which buttons show) was done correctly.

## Approach

1. Decide the trigger precisely, because "check every instruction" is too broad to survive. The
   narrow, checkable version: the instruction changes behaviour in a file whose current shape came
   from a ticket Claude can name. That is discoverable from `git log -S` plus the commit subject's
   ticket id, which this repo's commit convention guarantees.
2. Decide where it lives. Options, in rough order of preference:
   - A line in the global `CLAUDE.md` Execution Discipline section, next to "verify root cause
     first" and "check git log before designing fix", which are the same family.
   - A step inside `/do` and `/ticket`, so it fires when a session is already ticket-aware.
   - A hook is probably wrong here: the trigger is semantic, not textual.
3. Decide the response shape. It should be a question card, not a refusal, and it should quote the
   ticket line it is challenging so Joe can overrule in one read. The wrong shape is a warning
   Claude prints and then proceeds past.
4. Check the interaction with the existing "rejected question overrides standing approval" and
   "don't re-scope a plain instruction" rules, so this does not become a licence to relitigate
   ordinary instructions.

## Acceptance

- The rule exists in one named place, with the sc-55729 case as its worked example.
- The trigger is written narrowly enough that a session can tell whether it fires, without
  re-reading every ticket for every instruction.
- A session given "change X" where X traces to a ticket requirement asks once, quoting the
  requirement, and proceeds on Joe's answer.

## Notes

Open and unresolved as of filing: bea5f50 is pushed with the two-second revert in place. Whether
that gets fixed, and whether sc-55729 is re-opened for it, is Joe's call and is not part of this
todo. This todo is only about the rule.
