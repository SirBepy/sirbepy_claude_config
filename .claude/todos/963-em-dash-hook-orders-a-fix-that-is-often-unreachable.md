<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=8, reconfirm-count=1, content-hash=92f2728f -->
<!-- duplicate-checked -->
<!-- em-dash-exempt --> <!-- the Context block quotes the hook's own error text verbatim, em dash included -->
# The em-dash Stop hook orders an update_message fix that is often out of reach

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop the em-dash Stop hook from instructing a repair that the `update_message` tool structurally
cannot perform, so a flagged message either gets genuinely fixed or is reported as unfixable instead
of silently staying wrong.

## Context

Hit 2026-09-05 in a `countoff` `/mega-todos` session. The Stop hook fired:

> Em dash (U+2014) found in `mcp__cc_conductor__send_message` (text) near: "... - `fde6344` **11**
> — setup is now an ord...". Global rule bans it outright, rewrite using a comma, colon, or hyphen
> instead. That message already reached its recipient; revise it with
> `mcp__cc_conductor__update_message` (newest ordinal first).

That instruction could not be carried out. `mcp__cc_conductor__update_message`'s own description
states its reach:

> **Window:** you can only reach messages sent since Joe's second-most-recent message. Anything
> older is out of reach and the call is ignored.

The flagged bubble was sent during a long autonomous run, several dev turns earlier. By the time the
hook's feedback was acted on, the bubble was outside that window, so the repair call would have been
silently ignored. Nothing in the hook's message says this is possible, so the natural outcomes are
either a no-op call that reads as success, or (what actually happened) the agent noticing the
mismatch by hand and reporting it in prose.

**The window is the more likely case, not the edge case, for exactly the sessions this hook targets.**
A long unattended run sends many `send_message` bubbles between dev turns; the hook fires at Stop,
which can be several bubbles later.

## Approach

- Have the hook check reachability before prescribing `update_message`. If it cannot determine
  reachability, soften the instruction to name both branches rather than one: revise it if it is
  still in `update_message`'s window, otherwise state the correction in the next message.
- Cheaper alternative if reachability is not computable from the hook's payload: change the wording
  to "revise it with `mcp__cc_conductor__update_message` if it is still within that tool's window
  (messages sent since Joe's second-most-recent message); if it is older, say the correction plainly
  in your next message instead of silently leaving it."
- Best fix, if the payload allows it: catch the em dash at `PreToolUse` on `send_message` and BLOCK,
  so the bubble never reaches Joe and no after-the-fact repair is needed. A Stop-time catch is
  inherently a repair, and this one is a repair that often cannot run. Check whether the existing
  hook already has a PreToolUse counterpart before adding a second one.

## Acceptance

- The hook never instructs a repair it can know is impossible.
- A flagged message outside `update_message`'s window produces an instruction the agent can actually
  follow.
- The existing detection behaviour (which correctly caught a real em dash) is unchanged, and the
  hook's own self-test still passes under `python ci/run_all.py`.

## Notes

The detection half worked exactly as designed: it caught a genuine violation of the global no-em-dash
rule in outbound text, which is the whole point. Only the prescribed remedy is wrong. Do not weaken
the matcher while fixing the instruction.
