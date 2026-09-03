<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Checked in full against 858 (ground check's verdict for an OPEN tracker hit - about whether to
     create at all, mine is about what to ask once creating is settled), 498 and 502 (both /commit
     step 8's overlap question, a question that CANNOT be front-loaded). Shared vocabulary only. -->
# /ticket create mandates a question the dev's own invocation already answered

**Type:** skill-improvement
**Origin:** ai

## Goal

Give `/ticket`'s create path a defined behaviour when the dev's invocation is already an explicit
"file it" directive, so the mandatory front-loaded question either fires with a stated reason or is
skipped by rule, instead of being skipped by judgement as it was on 2026-09-01.

## Context

Hit 2026-09-01 in `zng-app`. The dev answered an `ask_user_question` card with "File a BE ticket,
also give me a msg to send to stevan and say i made the ticket already and gimme d link in d msg".

`skills/ticket/SKILL.md` create step 2 says:

> ### 2. Front-load the questions
> One `AskUserQuestion`, never open-ended, skipping anything the invocation already answered.

and `shortcut.md` names the four: title, epic, priority, estimate.

The session skipped that card entirely and applied defaults (epic 54968, priority High, estimate 1,
owner Stevan), reporting them in the result line per create step 5. Reasoning at the time: in
Conductor, `mcp__cc_conductor__ask_user_question` ends the turn ("do NOT keep working... the user
will reply in a separate follow-up message"), so asking would have split a two-minute ticket into
two round trips for four low-stakes defaults the dev can edit in Shortcut in seconds. The ticket
landed correct (sc-55338) and the dev did not object, but the skip was a judgement call against an
explicit skill rule, which is exactly the failure mode `/close` phase 1 step 4 exists to surface.

Distinct from [[502-commit-and-claude-md-contradict-on-asking-mid-task]]: 502 is about a question
that CANNOT be front-loaded (the overlap is unknowable until the diff exists). This one CAN be
front-loaded and CLAUDE.md fully permits it; the cost is purely the Conductor turn boundary.

## Approach

1. Re-read `skills/ticket/SKILL.md` create steps 2 and 5 and `shortcut.md`'s "Create specifics"
   question list. Confirm the rule still reads as quoted.
2. Decide with Joe which shape wins:
   - **Always ask, accept the round trip.** Simplest, keeps the rule absolute. Costs a turn on
     every create, including the ones where the dev already said "just file it".
   - **Defaults-with-disclosure carve-out.** When the invocation contains an explicit file-it
     directive, skip the card, apply the pinned defaults, and report every applied default in the
     result line (which step 5 already requires). Write the carve-out into step 2 so it is a rule,
     not a judgement.
   - **Ask only for the fields that are not mechanically derivable.** Epic is usually inferable
     from the affected code and title from the symptom; priority and estimate are not. Narrows the
     card to two options rather than removing it.
3. Whichever wins, state it in step 2 itself. Do not leave it to the per-tracker quirks files, or
   Shortcut and Linear will drift.

## Acceptance

- `skills/ticket/SKILL.md` create step 2 answers "the dev already said file it" explicitly, in one
  sentence, with no re-derivation needed.
- If the carve-out shape wins, it names the disclosure requirement in the same sentence, so a
  skipped card can never become a silent default.
- The chosen behaviour reads identically for Shortcut and Linear creates.

## Notes

Do not resolve this by weakening step 5's report line. The defaults-disclosure is what made the
2026-09-01 skip recoverable, and it is the part worth keeping under every candidate shape.

## Open questions

Written by /mega-todos on 2026-09-04. The next run opens with these.

- [ ] [TOOLING] When your invocation is already an explicit "file it" directive, should `/ticket` create still show the AskUserQuestion card? Options: always ask anyway / skip the card, apply defaults, and disclose them in the result line / ask only for fields that cannot be derived (priority, estimate). Recommended: skip and disclose. The todo's own Notes say disclosure is what made the skip recoverable the time you overrode it.
