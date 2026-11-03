---
name: zng-kickoff
description: Triggers on /zng-kickoff only. Daily ZNG hub chat - leftovers, Shortcut feed, todo and ticket triage with memory, then spawns work chats.
disable-model-invocation: true
---

# /zng-kickoff

> Daily ZNG starting point: find what needs the dev, then hand each piece to its own chat.

This chat is the hub for the day: the one chat the dev talks to. It does no work itself, ever. No
reading tickets or todos, no running scripts, no git, no code, no investigation. Everything,
triage included, goes to a spawned chat with a self-contained brief. The hub only talks to the
dev, asks questions (`ask_user_question`), shows its plan (`write_plan`), spawns chats
(`spawn_chat`), and routes (`list_peers`, `read_messages`, `send_message`). If the dev asks a
question that needs looking something up, spawn a chat for it; don't look it up here.

This rule holds for every request in this chat, not just the kickoff steps. If the dev says "go
check X" or "fix Y", that is a spawn, not an action.

Clockify is not part of this skill. A nightly Conductor schedule runs `/clockify-reconciliator`
separately.

## State and script

`scripts/kickoff.py` (run as `python -I <skill dir>/scripts/kickoff.py <cmd>`; the script sets its own UTF-8 stdout)
owns every fetch that has a cache. Its state lives in `~/.claude/state/zng-kickoff/`, which is
gitignored and machine-local. Each cache exists so the next day's run doesn't repeat work the dev
already finished:

| File | Remembers | Resurfaces when |
| --- | --- | --- |
| `feed.json` | Activity events (30 days), the newest event seen, handled marks per ticket | Someone other than the dev acts on the ticket after its handled mark |
| `todos.json` | Urgency verdict + content hash per todo file | The todo is new or its file changed |
| `tickets.json` | Dismissed pickup tickets + their `updated_at` | The ticket is updated after dismissal |

Never edit these files by hand. Use `handle`, `todo-verdict` and `ticket-dismiss`.

## Hub steps (what this chat does)

1. Call `write_plan` with: spawn the triage chat, relay its picks, spawn the chosen work chats.
2. Spawn ONE triage chat (cwd: the zng-app repo, name "ZNG triage"). Its prompt tells it to read
   this SKILL.md, run the "Triage procedure" below in full (steps 2-5), then stop and report: the
   top items, and a ranked list of workable picks with ticket links and verified state. It does no
   building and no ticket posting. It marks non-actionable items with `handle` / `todo-verdict` /
   `ticket-dismiss` as the procedure says.
3. When the triage chat reports (or the dev pastes its result), put the workable items in one
   `ask_user_question` card and spawn per the "Pick and spawn" rules below.
4. If the dev already named the work ("we had something today", "do X"), still spawn a chat to find
   and brief it; never go find it here.
5. When the dev asks what needs doing for one initiative or epic ("what else for zng-admin and
   zng-biller?"), spawn a scoping chat for that initiative across the repos. Do not fall back to the
   todo and feed triage: on 2026-11-02 that was the wrong reading and wrote 67 todo verdicts and 9
   handled marks the dev never asked for. Triage runs only when the dev asks what is on their plate
   overall.

`spawn_chat` allows one spawn per turn: spawn the first, say what is queued, spawn the next on the
dev's next message.

## Triage procedure (run by the triage chat, never by the hub)

The numbered steps below are written for the triage chat. Where they say "spawn" or "ask", the
triage chat reports to the dev instead and the hub does the spawning.

### 1. Plan

Call `write_plan` with steps 2-5 so the dev can skip one before it runs.

### 2. Leftovers

Run `kickoff.py leftovers` (fetches, then lists unpushed commits, dirty files and todo claims per
repo; a branch with no upstream prints `no upstream, N local commits`, and a failed fetch prints a
stale-state line). It ends with the `unsent drafts` block: every draft still waiting in the
Drafts panel from ANY chat in the project (topic, authoring chat, last update), read from
Conductor's drafts store on disk. Report those under Leftovers and give the oldest unsent ones a
"post it or drop it" line. The injected drafts list is not a substitute: it holds only drafts
written in the current chat, so it can never show an earlier chat's draft. A `no drafts store`
line means the store was unreadable: say so rather than reporting zero drafts. Add:
- `list_peers` with `scope: "all"`: ZNG chats still running, or ones that ended with work unpushed.

Unpushed commits are the top item. Name each one by subject, and say which spawned chat left it, if
the chat's name makes that clear.

### 3. Shortcut feed

Run `kickoff.py feed`. It fetches only events newer than the last run. On the first run it looks
back `--days` (default 3). A dead `SHORTCUT_SID` prints the refresh steps: relay them and skip to
step 4. A `WARNING` about the page cap means older events are still unfetched: run `feed` again
before trusting the list.

A ticket line followed by `DRAFT EXISTS: post it, do not redraft` already has an unsent draft
(matched by ticket id in the draft topic). Report it as "post the existing draft" with the draft's
topic and authoring chat, and never write a second draft for it. Only if the dev says the old draft
is stale does a chat redraft it.

For each listed ticket, follow `/shortcut-priorities` steps 4-7, but read the full ticket and
comments with `kickoff.py story <id>...` (one call for all ids: named state, owners, requester,
epic, links, description, every comment with author and date; GET only, never prints the token)
instead of hand-writing a fetch. Then drop off-plate states, cross-check git in the ZNG repos, and
rank it. Then:

- Nothing for the dev to do (FYI, someone else's thread, already answered, off-plate):
  `kickoff.py handle <id> --note "<why>"` right away, and don't report it.
- Actionable: report it. Mark it handled only once it's resolved in this chat (the dev answered, a
  draft was approved, or a chat was spawned for it).

### 4. Todos

Run `kickoff.py todos`. It prints per-repo counts (not urgent / urgent / to triage), the cached
urgent ones, and the todos that are new or changed.

Triage only the TRIAGE lines. Read each file, then decide:

- **urgent:** dev-origin and recent, a stated precondition is now met (check git, the way the
  2026-10-22 run caught a precondition commit that had already landed), it's in PLAN.md's top slot,
  or it blocks a push.
- **not-urgent:** anything else.

Record each one with `kickoff.py todo-verdict <repo> <file-or-id> <urgent|not-urgent> --reason "..."`.
A todo that is already done gets reported as "archive it", recorded not-urgent, and is never
archived from here.

Report the counts line per repo, then only the urgent ones.

### 5. Pickable tickets

Run `kickoff.py tickets`. It returns unstarted (Backlog / To Do) tickets under 90 days old that the
dev or Peter owns, or whose title has FE, Web App or Frontend as a word. BE-only titles are dropped, and tickets that were dismissed
and haven't changed are hidden.

For each one, read the ticket and comments with `kickoff.py story <id>...`, then check the code:

- Lives only in the old `lib/ui/loan_application/` flow (see the legacy-flow project memory).
- Waits on a BE change that hasn't landed.
- Already implemented: grep for the event or feature name.
- Already covered by step 2 or step 3.

Dismiss the dead ends with `kickoff.py ticket-dismiss <id> --reason "..."`. Report only the
workable ones.

### 6. Pick and spawn (hub only)

One `ask_user_question` card with `multiSelect`. Options are the workable items from steps 2-5, each
with the recommended / short-term / long-term badges where they apply.

`spawn_chat` allows **one spawn per turn**. Spawn the first pick, say which ones are queued, and
spawn the next one each time the dev sends a message.

Every spawn prompt stands alone, since the new chat can't see this one. It carries:

- the goal
- ticket links and verified state with receipts
- absolute file paths
- known traps
- constraints: local zng-api only, never the dev backend; commit via `/commit`; no ticket post or
  state change without the dev's OK on the exact text
- "keep messages short" if the dev said they're on their phone

## Hub mode (rest of the day)

- Talk to the dev, relay what spawned chats report, and spawn the next chat. Answers that need a
  lookup are a spawn, not a lookup (see the rule at the top).
- Drafts: spawn a chat to write them via `write_draft`. Slack drafts are plain text with no
  markdown links: the phone app's Copy pastes raw markdown into Slack (claude_usage_in_taskbar
  todo 1292).
- Every work-chat prompt ends with: when this item is resolved, run `kickoff.py handle` /
  `todo-verdict` / `ticket-dismiss` for it so tomorrow's run doesn't raise it again.

## Never

- Never does work in the hub chat: no tool calls beyond spawn/ask/plan/message/peers, no files, no
  scripts, no git. Delegate instead.
- Never posts a Shortcut comment or changes ticket state without the dev's OK on the exact text.
- Never archives or edits a todo in a ZNG repo. It only reports.
- Never re-raises a handled notification or a dismissed ticket that hasn't changed.
