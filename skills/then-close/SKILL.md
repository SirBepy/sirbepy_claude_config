---
name: then-close
description: Triggers on /then-close anywhere in a message. Finishes the task and any open work, then runs /close.
---

# /then-close

> Do the thing, then close. One token instead of typing "close when done".

**Trigger:** `/then-close` anywhere in a dev message - first, last, or on its own. Never auto-invoke.

Stays model-invocable (no `disable-model-invocation`) on purpose: Claude Code only expands a slash
command at the very start of a prompt, so `fix the typo /then-close` arrives as plain text and
Claude has to recognise the token and load this skill through the Skill tool itself. Flagging it
would make the trailing form silently do nothing.

The name deliberately does not start with `close`: Conductor marks a chat "Closing" the moment a
prompt begins with `/close` (see `close/SKILL.md`'s "Host app integration"), so a `/close-...` name
would flip the row to Closing before the work had even started.

## What the task is

- **With text** (`/then-close fix the typo`, or `fix the typo /then-close`): the task is the rest of
  the message. Any other `/command` in it is part of the task and runs before `/close`, per
  `~/.claude/refs/slash-arg-parsing.md`.
- **Alone** (pasted after a long back-and-forth): the task is everything still open in this session,
  the same list `/close` Phase 0 builds - every request the dev made that is not done yet, plus
  Claude's own unexecuted offers the dev said yes to. Nothing open: go straight to `/close`.

## Procedure

1. Do the task under every normal rule: testing floor, `/commit` per the auto-commit policy. This
   grants no push; a push still needs the dev to ask for it.
2. **Never close on an open question.** If the work stops on something only the dev can supply - a
   decision card, a blocker, a red check Claude cannot fix, a physical action - ask it and end the
   turn with status `question`. The `/then-close` stays armed: once the answer arrives and the work
   finishes, continue to step 3 without being told again. A dev message that drops or redirects the
   task disarms it.
3. Invoke `/close` through the Skill tool. Its Phase 0 runs as usual, but the dev already answered its
   fork by typing `/then-close`: for anything it finds unfinished that Claude can do alone, pick
   **Finish it first** without posting the card, do it, then let `/close` continue. Post the card only
   for an item that needs the dev, which is step 2's case again.
