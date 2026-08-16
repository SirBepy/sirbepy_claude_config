---
name: shortcut-pickup-ticket
description: Looks up a Shortcut story by ID, ALWAYS reads its full description and every comment before doing anything else, cross-references existing code/commits, and hands off to the dev.
disable-model-invocation: true
argument-hint: "<ticket-id>"
---

# /shortcut-pickup-ticket

> Pick up a Shortcut story and get fully briefed on it before starting work.

**Trigger:** `/shortcut-pickup-ticket <ID>` only — never on bare phrases like "check out 54229" (ambiguous across Shortcut/Obsidian/Linear/Trello); the **Step 2 rule** below still applies any time a Shortcut story is fetched for any reason.

## Why this skill exists

Reading only a story's `description` misses real requirements. Comments are where scope actually gets revised: a QA note flagging a bug the description never mentioned, a reviewer pushing back on the approach, a "let's do X instead." (Caught live on sc-54229: the description said nothing about horizontal scrolling, but a comment did - and it was the actual ask.) A skipped comment reads as a clean pickup and ships wrong.

## Fixed identity & constants

Shared across the shortcut-* skills: `~/.claude/refs/shortcut-api.md` (token extraction, dev UUID/mention/git author, workflow-state IDs).

## Step 1 - Parse the ID

- Expected invocation: `/shortcut-pickup-ticket <ID>` (e.g. `/shortcut-pickup-ticket 54229`). Shortcut story IDs are bare numbers - accept with or without an `sc-` prefix.
- If no argument was passed, search the dev's own tickets and ask which one via AskUserQuestion. Use the `Searching stories` recipe in `~/.claude/refs/shortcut-api.md` with `query=owner:josipmui !is:archived`, `page_size=10`.

## Step 2 - Fetch the full story: description AND every comment, ALWAYS

**Non-negotiable, every single pickup, no exceptions** - even if the ticket "looks simple" or the dev only asked to start it.

```bash
TOKEN=$(grep -a SHORTCUT_API_TOKEN ~/.claude/.env | sed 's/^\xef\xbb\xbf//' | cut -d= -f2 | tr -d '\r\n')
curl -s "https://api.app.shortcut.com/api/v3/stories/<id>" -H "Shortcut-Token: $TOKEN" -o C:/tmp/sc_<id>.json
```

Read the full JSON, not just `description`:

- `description` - the spec/AC as originally filed.
- `comments[]` - **every single one, in chronological order.** A comment can silently reverse, narrow, or add scope the description never mentions. Never sample, never skim just the last one, never skip because there are "a lot."
- Any image attached to a comment (`![...](https://media.app.shortcut.com/...)` in the comment text): download it with the same `Shortcut-Token` header (attachments are auth-gated) and view it with Read - a screenshot is often the clearest statement of the actual bug:
  ```bash
  curl -s "<attachment-url>" -H "Shortcut-Token: $TOKEN" -o C:/tmp/sc_<id>_<n>.png
  ```
  These downloads (`C:/tmp/sc_<id>.json`, `C:/tmp/sc_<id>_<n>.png`) are scratch - safe to delete any time, never referenced again after this step's summary is produced.
- `workflow_state_id` - current board column.
- `blocked` / `blocker` and `story_links` - if it blocks or is blocked by another story, fetch that story's `name` at minimum so the dependency is visible in the summary.
- `branches`, `pull_requests`, `commits` - existing work already in flight.

## Step 3 - Cross-reference the code

In the current repo (and any sibling repos the project's own CLAUDE.md names as in-scope for cross-repo work):

```bash
git log --all --oneline -E --grep="^${id}:"
```

If nothing matches by prefix, also try a broad `--grep "$id"` to catch bundled references, but confirm any hit is actually about this ticket before treating it as related work (a 5-digit number can coincidentally match unrelated text).

## Step 4 - Summarize before doing anything else

One tight paragraph, always covering:

- What the ticket asks for, per the description's AC.
- Current workflow state, and whether `branches`/`pull_requests`/`commits` show work already started.
- **Called out explicitly, not buried:** anything the comments changed, added, or contradicted relative to the description. If comments added nothing beyond the description, say that too, so it's clear they were actually read.
- Any blocking/blocked-by relationship from `story_links`.

## Step 5 - Move to In Progress (ask first)

Shortcut state is shared, team-visible state - never move it silently. Ask via AskUserQuestion:

- If `workflow_state_id` is `500018253` (Backlog) or `500018254` (To Do): offer to move it to `500018255` (In Progress) now, or leave it as-is.
- If it's already further along (PR Review, Testing, Blocked, etc.), do NOT offer to move it backward to In Progress - flag the mismatch instead (e.g. "board says PR Review but no open PR exists") and let the dev decide.

Only mutate on explicit go-ahead:

```bash
curl -s -X PUT "https://api.app.shortcut.com/api/v3/stories/<id>" \
  -H "Shortcut-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"workflow_state_id":500018255}'
```

Never include `custom_fields` in this PUT - it would replace the entire array.

## Step 6 - Hand off

Ask the dev what he wants to do next via AskUserQuestion:

- Start implementing
- Plan the approach first
- Just wanted the context, no action yet
- Something else

## What this skill never does

- Never skips or samples comments - every comment, every time, no exceptions.
- Never moves a ticket's workflow state without explicit per-ticket go-ahead.
- Never posts a comment.
- Never includes `custom_fields` in a PUT (would wipe the rest of the array).
- Never treats a commit-message ID prefix as proof of scope match without reading the actual diff, if code cross-referencing turns up a hit.

## Out of scope

- Creating tickets -> `/shortcut-create-ticket`.
- Auditing whether already-shipped work matches a ticket -> `/shortcut-done-audit`.
- Closing tickets or moving to Complete/Won't do -> manual, or a future skill.
