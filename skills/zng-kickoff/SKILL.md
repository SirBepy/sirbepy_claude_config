---
name: zng-kickoff
description: Triggers on /zng-kickoff only. Daily ZNG hub chat - leftovers, Shortcut feed, todo and ticket triage with memory, then spawns work chats.
disable-model-invocation: true
---

# /zng-kickoff

> Daily ZNG starting point: find what needs the dev, then hand each piece to its own chat.

This chat is the hub for the day. It triages, answers, drafts, and spawns. It never builds: every
piece of real work goes to a spawned chat with a self-contained brief.

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

## Steps

### 1. Plan

Call `write_plan` with steps 2-6 so the dev can skip one before it runs.

### 2. Leftovers

Run `kickoff.py leftovers` (fetches, then lists unpushed commits, dirty files and todo claims per
repo). Add:

- Open drafts from the injected drafts list that are still unsent.
- `list_peers` with `scope: "all"`: ZNG chats still running, or ones that ended with work unpushed.

Unpushed commits are the top item. Name each one by subject, and say which spawned chat left it, if
the chat's name makes that clear.

### 3. Shortcut feed

Run `kickoff.py feed`. It fetches only events newer than the last run. On the first run it looks
back `--days` (default 3). A dead `SHORTCUT_SID` prints the refresh steps: relay them and skip to
step 4.

For each listed ticket, follow `/shortcut-priorities` steps 4-7: read the full ticket and comments
via the public API, drop off-plate states, cross-check git in the ZNG repos, and rank it. Then:

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
dev or Peter owns, or with an FE title. BE-only titles are dropped, and tickets that were dismissed
and haven't changed are hidden.

For each one, read the ticket and comments, then check the code:

- Lives only in the old `lib/ui/loan_application/` flow (see the legacy-flow project memory).
- Waits on a BE change that hasn't landed.
- Already implemented: grep for the event or feature name.
- Already covered by step 2 or step 3.

Dismiss the dead ends with `kickoff.py ticket-dismiss <id> --reason "..."`. Report only the
workable ones.

### 6. Pick and spawn

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

- Answer follow-ups here. Re-read live state before asserting anything, per the global evidence rule.
- Drafts go through `write_draft`. Slack drafts are plain text with no markdown links: the phone
  app's Copy pastes raw markdown into Slack (claude_usage_in_taskbar todo 1292).
- When a reported item gets resolved, run `handle` / `todo-verdict` / `ticket-dismiss` so tomorrow's
  run doesn't raise it again.

## Never

- Never posts a Shortcut comment or changes ticket state without the dev's OK on the exact text.
- Never builds in this chat.
- Never archives or edits a todo in a ZNG repo. It only reports.
- Never re-raises a handled notification or a dismissed ticket that hasn't changed.
