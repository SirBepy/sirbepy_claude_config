<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=7, reconfirm-count=1, content-hash=c7a1f965 -->
<!-- duplicate-checked: searched this backlog for "send_message", "daemon-meta", "stop guard", "report_turn_status" and "peer relay". The near hits are 453 (silent.md duplicating terse-replies.md, a tone-ownership question) and 491 / done-332 (a skill-name hook firing on relayed peer text, a different hook and a different trigger). Neither covers two live rules disagreeing about whether a peer-relay turn owes a send_message. -->
# send-message-stop-guard contradicts the daemon-meta exception it is supposed to coexist with

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-27

## Goal

Make the send_message obligation and the daemon-meta relay exception agree, so a session following
one is not blocked by the other.

Filed from a `cueline` session, per root `CLAUDE.md`'s allocation rule: the fix lives in the global
tree, so it belongs in this backlog and not in the project's.

## Context

Incident, 2026-09-26, cueline session `4252077a`, during an `/auto-do-todos` run alongside a second
Conductor session in the same repo. `hooks/send-message-stop-guard` fired **twice**:

```
[send-message-stop-guard] 3 consecutive turns have ended via report_turn_status with no
send_message - call mcp__cc_conductor__send_message with a status summary before ending this turn.
(todo 410: a quiet turn or two is fine, a whole silent stretch is not.)
```

and again later with `4 consecutive turns`.

**Both stretches were turns the session was explicitly told NOT to message on.** The session-specific
instruction block carries this exception verbatim:

> Exception: a turn whose only input is a `[daemon-meta]`-tagged relay (inter-agent coordination-channel
> broadcast, Jarvis message, schedule wake) that needs no reply or action from you - pure peer chatter
> that changes nothing about your own work - only owes `report_turn_status(done)`; skip `send_message`
> there, it will not be blocked.

The run had a long stretch of exactly that: peer messages announcing file lanes, test-suite
start/exit, and claim handoffs. Each needed a `post_message` reply to the peer and nothing for Joe.
The exception says those turns are fine and "will not be blocked". The guard blocked them anyway,
because it counts consecutive `report_turn_status`-only turns without knowing why they were silent.

So the failure is not a session ignoring a rule. It is two rules that cannot both be satisfied, and
the session complied with the stricter one by writing status summaries Joe did not need, which is
precisely the noise `refs/...`'s "peer coordination is invisible plumbing" guidance exists to prevent.

The promise "it will not be blocked" is false as written, and that is the part worth fixing: a rule
that states a mechanical guarantee the mechanism does not honour teaches the reader to distrust the
next such guarantee.

## Approach

1. Decide which rule wins, and make it mechanical rather than advisory:
   - **Option A, teach the guard about relay turns.** The guard already sees the turn's input. If the
     only user-side input was `[daemon-meta]`-tagged, do not increment the consecutive counter. This
     is the option that makes the existing exception's promise true, and it is a string check on a
     tag the harness already emits.
   - **Option B, drop the exception.** Require a `send_message` on every turn including relay-only
     ones, and accept the noise. Cheapest to implement, worst outcome: it manufactures exactly the
     peer-coordination chatter the `send_message` tool description tells sessions not to send.
   - **Option C, raise the threshold.** Leave both as-is and bump the counter from 3 to something
     higher. Does not fix the contradiction, just makes it fire less often. Reject explicitly rather
     than by omission.
   Option A is the recommendation.
2. If A: also decide whether a relay turn that DID change the session's own work (the peer said
   something that altered a plan) should still count. It probably should, since that is a real
   thing Joe would want surfaced, and the exception's own wording already turns on "changes nothing
   about your own work" rather than on the tag alone. Note that the tag is checkable and the
   "changed my work" condition is not, so A can only approximate the exception, and that gap should
   be stated in the rule rather than left implicit.
3. Whichever is chosen, correct the sentence "skip `send_message` there, it will not be blocked" so
   it describes what actually happens.

## Acceptance

- A relay-only turn either genuinely does not trip the guard, or the exception no longer claims it
  will not be blocked.
- The rejected options are recorded with their reasons, so the next reader does not re-propose
  raising the threshold.
- The gap between "tagged as a relay" (checkable) and "changed nothing about my own work" (not
  checkable) is stated wherever the final rule lives.

## Notes

- The guard's own message cites todo 410, so its intent is documented and correct: a whole silent
  stretch IS worth catching. This todo is not an argument against the guard, only against it
  counting turns the rules elsewhere told the session to keep silent.
- Adjacent but distinct: todo 453 asks which file owns Joe's chat-tone rules. If that gets resolved
  by consolidating into one file, this exception's wording should land in the same place.
