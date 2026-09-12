<!-- Claim before executing: .claude/todos/.claims/993-the-message-em-dash-check-fires-after-the-message-is-sent.md -->
<!-- duplicate-checked -->
<!-- checked against 986 (untracked, filed by a concurrent session 2026-09-12): that one is about
     the em-dash prefilter scanning text-like binaries such as PDFs, a false-positive problem in the
     COMMIT prefilter. This is about WHEN the check runs for chat messages, a timing problem in a
     different hook. Also checked 290 and 791 in done/: both concern a builder emitting em dashes in
     new file content, not chat messages. None of the three is this. -->
# The em-dash check on chat messages runs after the message has already been sent

**Type:** skill-improvement
**Origin:** ai

## Goal

Catch a banned character in a `send_message` before it reaches the dev, not after.

## Context

Observed twice in one session on 2026-09-11 and 2026-09-12, by the same session, which is what makes
it worth filing rather than filing under carelessness.

Global `CLAUDE.md` bans the em dash outright. For chat messages the enforcement is a **Stop** hook,
so the sequence is: the message is composed, sent, delivered to the dev, and only then does the hook
fire and report the violation. The remedy it prescribes is `mcp__cc_conductor__update_message`, which
silently swaps the bubble in place.

That works, and both violations were corrected within a turn. But it means:

- The dev can read the offending text before the correction lands. The window is small and real.
- The correction depends on the message still being inside `update_message`'s reach (messages sent
  since the dev's second-most-recent message). Outside that window the hook's own instructions fall
  back to "say the correction plainly in your next message", which is strictly worse than not having
  sent it.
- Repetition is not deterred. The rule was in context both times; stating it again is what todo 290
  already established does not work ("a flag is a fix, never a louder restatement of the rule").

Compare the COMMIT path, which gets this right: `skills/commit/em-dash.sh` runs inside the prefilter
gate as a **PreToolUse** check, chained so a non-zero exit stops the commit before it happens. Same
rule, same character, one enforced before the fact and one after.

The asymmetry looks like history rather than a decision: the commit prefilter came first and the
message check was bolted onto the Stop event, which is the easy place to inspect a turn's output.

## Approach

1. Confirm the current wiring before changing it. Find which hook reports the message violation and
   on which event, in `settings.json` and under `hooks/`. Do not assume it is a single hook or that
   `Stop` is the only event involved.
2. Establish whether a `PreToolUse` matcher can see a `send_message` tool call's `text` argument at
   all in this harness. That is the load-bearing question and it is empirical: probe it with a
   harmless always-exit-0 logging hook in a scratch config, the way todo 434's probe was run, rather
   than reasoning from the event name. If the payload does not carry the text, this approach is
   closed and the todo should say so and stop.
3. If it does carry it, move the check to `PreToolUse` with a deny, so a message carrying the
   character is never delivered. Reuse the existing detection rather than writing a second one; two
   implementations of one rule is how they drift.
4. Keep the `Stop` check as a backstop only if step 3 leaves a gap it genuinely covers. Two hooks
   firing on the same rule for the same text is noise otherwise.

## Acceptance

- The empirical answer from step 2 is recorded in this todo or in the hook's comments, whichever
  survives, including the negative case if it is negative.
- If implemented: a `send_message` containing the character is blocked before delivery, proven by a
  real triggered attempt and not by reading the matcher.
- An ordinary message is unaffected, proven the same way. A chat hook that misfires is worse than
  the problem, since it blocks the only channel the dev reads.
- No second copy of the detection logic exists.
- `python ci/run_all.py` passes.

## Notes

- The character is not written literally anywhere in this file on purpose: the commit prefilter would
  flag it, which is the enforcement working correctly and is itself the point being made.
- Do not "solve" this by relaxing the rule for chat. The rule is stated as absolute and the dev has
  reaffirmed it; the problem is the timing of the check, not its strictness.
