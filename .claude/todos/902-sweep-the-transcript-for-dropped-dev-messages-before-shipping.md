<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# /close's transcript sweep catches dropped dev messages only after the work has shipped

**Type:** skill-improvement
**Origin:** ai

## Goal

Catch a dev instruction that never reached the working context BEFORE it is built on and pushed,
not during the retrospective afterwards.

## Context

Incident, countoff, 2026-09-03. Joe sent:

> 1. i dont like the grid that there isnt a real center
> 2. i dont like that its kinda side by side... i would wish it was centered i guess?

It is in the session transcript, between a `[daemon-meta]` peer relay and his next message
("continue"). It never appeared in the working context. The session answered "continue", then built,
committed, and **pushed** the side-by-side layout he had just rejected, plus deployed it to GitHub
Pages. Only `/close` Phase 1's transcript grounding found it, and by then the fix had to be a new
commit on top of a published one.

`/close`'s own transcript sweep is what caught it, so the mechanism works. The gap is purely
placement: `skills/close/SKILL.md`'s "Transcript grounding (long sessions only)" runs at Phase 1 of
`/close`, which is by definition the end of the session. Nothing runs it at a point where the answer
could still change what gets built.

`/commit` step 7a already calls `list_peers`/`post_message`, so the commit path knows about
concurrent sessions, but it checks for FILE collisions between sessions, never for a dev message
lost among their relays.

Not yet established: whether peer relays actually cause the drop. Two landed around the same moment,
which is correlation only. Worth confirming before writing a fix that assumes the cause.

## Approach

Options, in rough order of cost:

- Cheapest and most targeted: add a check to `skills/commit/SKILL.md` before its push subcommands
  (`push`, `pushbump`, `pushnbump`) only, not every commit. Grep the transcript's `"type":"user"`
  text turns since the session's previous push and confirm each was acknowledged. A push is the
  point where the cost of having missed something jumps, so it earns a gate that a local commit
  does not.
- Alternative: fire it from the peer path instead, in whatever handles `[daemon-meta]` relays, so a
  relay arriving is itself the trigger to re-read recent user turns.
- Reject the "always sweep before every commit" version. Transcripts are megabytes and the grep is
  not free; a per-commit gate would tax every routine commit to catch a rare failure.

Whichever is picked, reuse `skills/close/SKILL.md`'s existing resolution recipe verbatim
(`~/.claude/sessions/*.json` for the sessionId, then the sanitised-cwd folder) rather than
re-deriving the path, and keep its `Grep`-never-`Read` rule.

## Acceptance

- A session that receives a user message which never enters its context is stopped before pushing,
  and names the unaddressed message.
- The check does not run on plain `/commit` with no push subcommand.
- A session with no peer relays and no missed messages sees no added output.

## Notes

The countoff-side record of the same incident is the `joes-messages-can-be-lost-among-peer-relays`
project memory, which holds the verbatim quote and the file path.
