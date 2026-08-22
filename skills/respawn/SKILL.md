---
name: respawn
description: Close this chat and hand its work to a fresh one, carrying the whole context in a visible first message.
disable-model-invocation: true
argument-hint: "[optional note / model override, e.g. `opus` or `focus on the daemon half`]"
---

# /respawn

> This chat is replaced, the work survives. One call spawns a successor in the same project, hands
> it everything as a real visible message, and closes this chat at turn end.

Replaces Claude Conductor's retired "Handoff to next AI" menu button, which hid its context in
`.for_bepy/HANDOFF.md` and coordinated through a `<HANDOFF_READY/>` sentinel. Both are gone. The
context now lives in the successor's first user message, where Joe can read it.

**Requires the `respawn` MCP tool** (Conductor-hosted sessions only). If it isn't in your tool
list, stop and say so - do not fall back to `spawn_chat` + `close_session`, do not write a handoff
file, and do not close.

`respawn` does both halves in one call, so there is no ordering to get wrong and no separate
`close_session`. It also stamps `successor_of` on the new chat, which is what makes the app move
Joe onto the successor in place - same window, same sidebar slot, composer draft intact. The
visible messages do NOT carry over; that is the point, and it is why `prompt` has to restate
everything.

Do not use `spawn_chat` here. That one starts a chat that runs ALONGSIDE this one, sets no
successor link, and closes nothing.

## What this is NOT

- **No `/code-check`.** Backlog sweeps are deliberate work Joe runs himself. Skipped by design.
- **No commits.** Respawn's own invocation takes a freeform note/model override, never a chained
  command, so `/close`'s Phase 5 (run chained commands, where `/commit` would live) never fires
  here. The successor inherits the same dirty tree and continues the same work, so nothing is at
  risk of being lost - but that makes Phase 4's git snapshot below load-bearing, not optional. A
  successor that doesn't know what's half-finished in its own tree starts blind.
- **No handoff file.** If Joe wants a durable record instead of a live pickup, that's `/handoff`,
  which is a different gesture: defer without picking up.

## Phases 0-3 - run /close verbatim, minus code review

Run `/close --skip-review --dont-close`'s Phases 0, 1, 3, and 4 exactly as written in
`~/.claude/skills/close/SKILL.md` - no respawn-specific overrides:

- **Phase 0 - Safe-to-close check.** Same AskUserQuestion prompt when Joe is watching an
  unfinished dev commitment. Unfinished items get filed as todos in Phase 3 below exactly like a
  normal close - this skill's own handoff prompt (Phase 4 below) surfaces them to the successor
  live on top of that, it doesn't replace the todo.
- **Phase 1 - Retrospective.** Including the transcript-grounding step for long sessions. Print
  nothing here - Phases 3 and 4 (of this skill) consume it.
- **Phase 3 - Persist.** All three steps: memory writes through the rubric gate, todo files for
  every qualifying item, and the screenshot summary count.
- **Phase 4 - Counter summary.** Print the one-line counter, same format as a normal close.

## Phase 4 - Compose the handoff prompt

This is respawn's own addition on top of /close. Joe reads this message, so lead with what he'd
want to see at a glance and put the depth underneath.

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

## Phase 5 - Respawn

Call `respawn` with `cwd` = this session's own cwd and `prompt` = Phase 4's text. Omit `model` and
`effort` so the successor inherits this chat's model, effort, account, character and auto-accept -
unless the invocation named an override (`/respawn opus`).

The tool refuses a cwd that isn't this session's own, and refuses a second spawn in the same turn.
Both refusals mean something is wrong with the call, not with the daemon - fix the call, and if
the second one fires, you already respawned: do NOT retry, go straight to Phase 6.

On `{ok: false}`: stop. Report the error and leave this chat open. Nothing was closed, so the
session is intact - a retry or a manual handoff is still possible.

## Phase 6 - Close

The close is already done: `respawn` flagged this chat and its own pump tears it down at turn end.
Do NOT call `close_session` - it is redundant here.

Tell Joe the successor's session id, then run the rename/kill script from `/close`'s Phase 6:

```powershell
& "C:\Users\tecno\.claude\skills\close\rename-session.ps1" -Close
```
