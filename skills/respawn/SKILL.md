---
name: respawn
description: Close this chat and hand its work to a fresh one, carrying the whole context in a visible first message.
disable-model-invocation: true
argument-hint: "[optional note / model override, e.g. `opus` or `focus on the daemon half`]"
---

# /respawn

> This chat dies, the work survives. Spawn a successor in the same project, hand it everything as
> a real visible message, then close.

Replaces Claude Conductor's retired "Handoff to next AI" menu button, which hid its context in
`.for_bepy/HANDOFF.md` and coordinated through a `<HANDOFF_READY/>` sentinel. Both are gone. The
context now lives in the successor's first user message, where Joe can read it.

**Requires the `spawn_chat` MCP tool** (Conductor-hosted sessions only). If it isn't in your tool
list, stop and say so - do not fall back to writing a handoff file, and do not close.

## Hard ordering rule

`spawn_chat` FIRST, `close_session` second. `close_session` kills the process that would make the
spawn call, so a close-then-spawn ordering silently loses the successor and the context with it.

## What this is NOT

- **No `/code-check`.** Backlog sweeps are deliberate work Joe runs himself. Skipped by design.
- **No commits.** The successor inherits the same dirty tree and continues the same work, so
  nothing is at risk of being lost - but that makes Phase 3's git snapshot load-bearing, not
  optional. A successor that doesn't know what's half-finished in its own tree starts blind.
- **No handoff file.** If Joe wants a durable record instead of a live pickup, that's `/handoff`,
  which is a different gesture: defer without picking up.

## Phase 0 - Safe-to-close

Run `/close`'s Phase 0 verbatim (`~/.claude/skills/close/SKILL.md`), with one change: an unfinished
item is NOT filed as a todo. It goes into Phase 3's "Where it stalled" and "Next steps" instead -
the successor is about to start work, so handing it the item beats parking it in a backlog.

Still ask Joe the "finish it first / hand it over" question when he's watching, same as /close.

## Phase 1 - Retrospective (internal)

Run `/close`'s Phase 1, including its transcript-grounding step for long sessions. Print nothing.
It exists here only to feed Phase 2's memory writes and Phase 3's prompt.

## Phase 2 - Memory writes

`/close`'s Phase 3 step 1, unchanged: route each correction and confirmed non-obvious fact through
`~/.claude/refs/memory-rubric.md`'s ADD/UPDATE/DELETE/NONE gate. NONE is a normal outcome.

## Phase 3 - Compose the prompt

This is the whole skill. Joe reads this message, so lead with what he'd want to see at a glance
and put the depth underneath.

```
We're continuing <one line: the original ask, not the last subtask>.

**Done so far:** <2-4 sentences>
**Where it stalled:** <what's blocking, or "nothing - just out of context">
**Next steps:**
1. <concrete>
2. <concrete>

**Uncommitted on purpose** - branch `<branch>`, nothing was committed during the handoff:
<`git status --short` output>

**Decisions already settled** (do not re-litigate):
- <decision + why>

**Corrections Joe made this session:**
- <what was wrong, what he wanted instead>
```

Fill the git block from real command output this turn (`git rev-parse --abbrev-ref HEAD`,
`git status --short`), never from memory of what you edited. An empty `git status` means say
"clean tree", not an empty block.

Length: long is fine where it helps the successor, but the first six lines must stand alone as a
summary Joe can skim. If everything above the git block runs past ~15 lines, the summary is doing
too much work - cut, don't reword.

If the invocation carried a freeform note, honor it in the prompt; it never overrides the derived
context, it adds to it.

## Phase 4 - Spawn

Call `spawn_chat` with `cwd` = this session's own cwd and `prompt` = Phase 3's text. Omit `model`
and `effort` so the successor inherits this chat's model, effort, account, character and
auto-accept - unless the invocation named an override (`/respawn opus`).

The tool refuses a cwd that isn't this session's own, and refuses a second spawn in the same turn.
Both refusals mean something is wrong with the call, not with the daemon - fix the call, and if
the second one fires, you already spawned: do NOT retry, go straight to Phase 5.

On `{ok: false}`: stop. Report the error and leave this chat open. A failed spawn followed by a
close loses the session for nothing.

## Phase 5 - Close

Tell Joe the successor's session id, then run `/close`'s Phase 6 exactly: `close_session` first,
the rename/kill script second. That ordering is a hard rule over there and it holds here.
