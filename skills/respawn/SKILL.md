---
name: respawn
description: Close this chat and hand its work to a fresh one, carrying the whole context in a visible first message.
disable-model-invocation: true
argument-hint: "[lite] [optional note / model override, e.g. `opus` or `focus on the daemon half`]"
---

# /respawn

> This chat is replaced, the work survives. One call spawns a successor in the same project, hands
> it everything as a real visible message, and closes this chat at turn end.

Replaces Claude Conductor's retired "Handoff to next AI" menu button, which hid its context in
`.for_bepy/HANDOFF.md` and coordinated through a `<HANDOFF_READY/>` sentinel. Both are gone. The
context now lives in the successor's first user message, where Joe can read it.

**Requires the `respawn` MCP tool** (Conductor-hosted sessions only). If it isn't in your tool
list, restart the app and retry first - MCP tools register at session start, so a session older
than the tool won't see it yet. If it's still missing after a restart, stop and say so - do not
fall back to `spawn_chat` + `close_session`, do not write a handoff file, and do not close.

This restart advice is about `respawn` specifically, because it lives in Conductor's own
generated per-session MCP config and can genuinely appear after a Conductor update. It does NOT
generalize to any other missing MCP tool (Roblox Studio, figma, a project's `.mcp.json` server,
etc.) - see `~/.claude/refs/conductor-mcp-constraint.md`: `--strict-mcp-config` makes Conductor's
generated config the only MCP source a chat ever sees, so a non-conductor tool that isn't there
cannot be made to appear by restarting, respawning, or editing config.

`respawn` does both halves in one call, so there is no ordering to get wrong and no separate
`close_session`. It also stamps `successor_of` on the new chat, which is what makes the app move
Joe onto the successor in place - same window, same sidebar slot, composer draft intact. The
visible messages do NOT carry over; that is the point, and it is why `prompt` has to restate
everything.

Do not use `spawn_chat` here. That one starts a chat that runs ALONGSIDE this one, sets no
successor link, and closes nothing.

## Modes

Too little context costs more than too much: a successor missing one correction repeats the
mistake, while one with an extra paragraph just skims it (Joe, 2026-10-28: "its always better to
give more info than not enough"). Both modes therefore record everything in the detail file
(Step 1); they differ only in how much the successor is made to read up front.

| | **Full** (default) | **Lite** (`/respawn lite`) |
|---|---|---|
| Used by | Joe typing `/respawn`; `/brainstorm`'s greenfield design-to-build hand-off | `/auto-respawn` and `/loop-todos`, the automatic respawns |
| /close phases | `/close --dont-close` Phases 0-4 as written | `/close --dont-close --light` Phases 0-4, with the two skips below |
| Visible prompt | Every section in Step 2 | The Lite subset in Step 2 |
| Detail file | Written | Written |

Lite's two skips, both because the caller already covers them:

- **Phase 0 never asks.** The automatic callers run unattended, so `/close`'s non-interactive
  branch applies: unfinished items are filed as todos, and they also go under the prompt's
  **Next steps** since the successor continues the same work.
- **Phase 2 is skipped when the caller already ran `/code-check` over this session's commits**
  (`/loop-todos` cycles run `/auto-do-todos`, whose Step 9 does this). Otherwise `/close`'s own skip rules decide, as in Full.

A leading `lite` token selects Lite. Any other argument is a freeform note or a model override.

## What this is NOT

- **No commits.** Respawn's own invocation takes a freeform note/model override, never a chained
  command, so `/close`'s Phase 5 (run chained commands, where `/commit` would live) never fires
  here. The successor inherits the same dirty tree and continues the same work, so nothing is at
  risk of being lost - but that makes Step 2's git snapshot below load-bearing, not optional. A
  successor that doesn't know what's half-finished in its own tree starts blind.
- **The detail file is overflow, never the handoff.** The retired `HANDOFF.md` failed because the
  context lived only in a hidden file. Here the visible prompt still carries everything the
  successor must act on; the detail file holds what it might want to look up. If dropping the file
  would leave the successor unable to do its next step, that content belongs in the prompt. For a
  durable record without a live pickup, use `/handoff`, a different gesture: defer without picking
  up.

## /close Phases 0-4

A respawn is a full `/close` that starts a new chat in its place (Joe, 2026-10-08: "/respawn should
always also do /code-check ... basically do the full /close, but then just start a new chat in its
place"). Run `/close --dont-close`'s Phases 0, 1, 2, 3 and 4 as written in
`~/.claude/skills/close/SKILL.md` (Lite: with `--light` and the two skips in Modes above):

- **Phase 0 - Safe-to-close check.** Same AskUserQuestion prompt when Joe is watching an
  unfinished dev commitment. Unfinished items get filed as todos in Phase 3 below exactly like a
  normal close - this skill's own handoff prompt (Step 2 below) surfaces them to the successor
  live on top of that, it doesn't replace the todo.
- **Phase 1 - Retrospective.** Including the transcript-grounding step for long sessions. Print
  nothing here - Steps 1 and 2 below consume it.
- **Phase 2 - Code health review.** `/code-check` over this session's own commits, with `/close`'s
  own skip rules (under 50 added lines, no code files). Its findings land in the backlog before the
  successor starts, so the detail file can name them.
- **Phase 3 - Persist.** Every step: memory writes through the rubric gate, todo files for every
  qualifying item, the screenshot summary count, the session digest, and deleting the detail file
  this chat inherited (if it was itself a respawn successor).
- **Phase 4 - Counter summary.** Print the one-line counter, same format as a normal close.

## Step 1 - Write the detail file

Overfill it. Nobody pays for it unless the successor opens it, so when unsure whether something
belongs, it belongs.

**Path:** next to this session's transcript, as `<sessionId>.respawn.md`. `<sessionId>` is
`$CLAUDE_CODE_SESSION_ID`; find the transcript with Glob `projects/*/<sessionId>.jsonl` under
`$CLAUDE_CONFIG_DIR` (`~/.claude` when unset). That folder sits outside every repo, so the file
never needs a gitignore entry, and `recall.py compress` archives only `.jsonl` files and session
folders, so it never sweeps the file away early.

1. Write the authored sections with the Write tool:

   ```
   # Respawn detail: <the original ask, one line>

   Predecessor session <sessionId>, <YYYY-MM-DD HH:MM>. Transcript: <absolute .jsonl path>

   ## Files touched
   - <absolute path> - <what changed and why>

   ## Commits this session
   - <short sha> <subject>   (from `git log`, never from memory; "none" if none)

   ## Verification
   - <command or check> - <result, with the failing output quoted when red>

   ## Todos filed and /code-check findings
   - <id> <title>   (from /close Phases 2-3; "none" if none)

   ## Retrospective
   </close Phase 1's bullets, including the ones it did not print>

   ## Facts, dead ends, live resources
   <the long form of the prompt's sections of the same names: the evidence behind each fact,
   the exact error each dead end produced, every port, id and path>

   ## Anything else
   <rejected options and why they lost, URLs, ticket ids, quoted errors, half-formed ideas>

   ## Conversation
   ```

2. Append the whole visible conversation (Joe's messages verbatim, Claude's chat bubbles, the
   question cards, commits) without passing it through this chat's context:
   `python ~/.claude/skills/recall/recall.py show <sessionId> --max-chars 400000 --append-to <path>`.
   The output stays inside recall's data fence, so the successor reads it as data, not orders.
3. Delete any `*.respawn.md` in the same folder older than 14 days. A chat closed without
   `/close` leaves its inherited file behind, and this is the only sweep that finds it.

## Step 2 - Compose the handoff prompt

This is the successor's first message, and Joe reads it too, so the first six lines must stand
alone as a summary he can skim. After those, Full has no length cap: add every section that has
content and drop a section only when it is genuinely empty. Lite keeps the sections marked
**(Lite)** and should fit in about 25 lines above the git block.

A caller that needs a slash command re-run (`/auto-respawn`, `/loop-todos ... --resumed`) puts it
as the prompt's literal FIRST characters, above everything below, since a slash command only
expands at the very start of a turn. Handing off a build phase after a design session, the prompt
may likewise open with `/autopilot`, since nothing else carries the intended mode forward.

```
We're continuing <one line: the original ask, not the last subtask>.            (Lite)

**Done so far:** <2-4 sentences>                                                 (Lite)
**Where it stalled:** <what's blocking, or "nothing - just out of context">      (Lite)
**Next steps:**                                                                  (Lite)
1. <concrete>
2. <concrete>

**Joe's original ask, verbatim:**
> <his first message on this work, quoted exactly>

**Decisions already settled** (do not re-litigate):
- <decision + why>

**Corrections Joe made this session:**                                           (Lite)
- <what was wrong, what he wanted instead>

**Facts learned and dead ends** (do not retry):
- <fact, with its receipt: file:line, command output, URL>
- <tried X, failed because Y>

**Verification state:** <what ran and passed, what failed, what never ran>

**Live resources:**                                                              (Lite)
- <supervised-run servers with id and port, background tasks or agents still running,
  claimed todos, open question cards, peers mid-coordination, or "none">

**Read first:**
- <absolute path> - <why>

**Uncommitted on purpose** - branch `<branch>`, nothing was committed during the handoff:   (Lite)
<`git status --short` output>

**More detail, only if needed:**                                                 (Lite)
- Detail file: <absolute path>. Holds the full conversation verbatim, files touched, commits,
  todos filed, /code-check findings and the retrospective. Temporary: this chat's /close deletes it.
- Previous transcripts, newest first: <this session's .jsonl path>, <every path listed on this
  line of this chat's own first message, if it was a respawn successor>. Grep them, never Read
  one whole, or run `python ~/.claude/skills/recall/recall.py show <sessionId> --grep <term>`.
```

Fill the git block from real command output this turn (`git rev-parse --abbrev-ref HEAD`,
`git status --short`), never from memory of what you edited. An empty `git status` means say
"clean tree", not an empty block. Outside a git repo, drop the block.

Live resources come from real state too: `sv.ps1 ls` (see `/supervised-run`) for supervised servers, `ListAgents`
for this session's own agents, `.claude/todos/.claims/` for claims this session holds. A
successor that does not know a server is running starts a second one on a new port.

If the invocation carried a freeform note, honor it in the prompt; it never overrides the derived
context, it adds to it.

## Step 3 - Respawn

Call `respawn` with `cwd` = this session's own cwd and `prompt` = Step 2's text. Omit `model` and
`effort` so the successor inherits this chat's model, effort, account, character and auto-accept -
unless the invocation named an override (`/respawn opus`).

The tool refuses a cwd that isn't this session's own, and refuses a second spawn in the same turn.
Both refusals mean something is wrong with the call, not with the daemon - fix the call, and if
the second one fires, you already respawned: do NOT retry, go straight to Step 4.

On `{ok: false}`: stop. Report the error and leave this chat open. Nothing was closed, so the
session is intact - a retry or a manual handoff is still possible. The detail file stays on disk
for that retry.

## Step 4 - Close

The close is already done: `respawn` flagged this chat and its own pump tears it down at turn end.
Do NOT call `close_session` - it is redundant here.

Tell Joe the successor's session id, and stop there. Do not run `/close`'s rename/kill script:
the pump already ends this chat, and in a Conductor chat that script refuses with exit 3 and a
`REFUSED: host-managed session ... call close_session` line. That line is expected after a respawn
and is never a reason to call `close_session`.
