---
name: trello
description: Manage Trello boards, lists, and cards via the REST API. Triggers on any mention of Trello - creating cards, scaffolding boards from a spec, bulk updates, moving cards, applying labels. Use when the user says "trello", "add a card", "create a board", "move this to done", etc.
---

# /trello

> Manage Trello boards, lists, and cards via the REST API.

the dev gives you a spec (plain text or markdown), you turn it into boards, lists, and cards.

## Setup check

Before ANY API call, verify auth is set up. Read `~/.claude/.env` and confirm `TRELLO_KEY` and `TRELLO_TOKEN` are both present.

If either is missing, STOP and tell the dev:

> Trello auth not set up. Add these to `~/.claude/.env`:
> ```
> TRELLO_KEY=...
> TRELLO_TOKEN=...
> ```
> Generate them at https://trello.com/power-ups/admin (create a Power-Up, then API Key tab, then click "Token" link).

Do NOT try to guess, prompt for credentials in chat, or store them anywhere else.

## Load env

Every invocation starts with sourcing the env file. One command per call, no chaining:

```bash
source ~/.claude/.env
```

Then verify:

```bash
echo "${TRELLO_KEY:?TRELLO_KEY not set}"
```

```bash
echo "${TRELLO_TOKEN:?TRELLO_TOKEN not set}"
```

## Core concepts

Trello's data model, smallest to largest:
- **Card** - the unit of work. Has name, desc, labels, members, checklists, due date.
- **List** - a column on a board (e.g. "Backlog", "Doing", "Done"). Holds cards.
- **Label** - colored tag attached to cards. Defined per-board.
- **Board** - holds lists and labels. Optionally inside a workspace.
- **Workspace (aka organization)** - a team/group that owns boards.

Hierarchy: workspace -> board -> list -> card. Labels live at the board level.

IDs look like `5abbe4b7ddc1b351ef961414` (24-char hex). Boards also have short IDs in URLs like `https://trello.com/b/dQHqCohZ` - the `dQHqCohZ` part works as an ID in most endpoints.

## API basics

- Base URL: `https://api.trello.com/1`
- Every request needs `key=$TRELLO_KEY&token=$TRELLO_TOKEN` as query params
- POST/PUT take params as query string OR form data - query string is simpler, use that
- Responses are JSON. Pipe through `jq` to extract fields.
- Rate limits: 300/10s per key, 100/10s per token. If you hit 429, wait 10 seconds and retry. For bulk ops, add a small sleep between calls.

### Request pattern

```bash
curl -sS --fail-with-body -X POST \
  "https://api.trello.com/1/cards?key=$TRELLO_KEY&token=$TRELLO_TOKEN&idList=$LIST_ID&name=My%20card"
```

- `-sS` = silent but show errors
- `--fail-with-body` = exit non-zero on HTTP errors, still show the body
- Always URL-encode values with spaces or special chars. Use `jq -sRr @uri` for this: `printf '%s' "My card" | jq -sRr @uri`

### Extracting IDs

Pipe through `jq` to grab IDs from responses:

```bash
curl -sS "..." | jq -r '.id'
```

For lists of things:

```bash
curl -sS "..." | jq -r '.[] | "\(.id)\t\(.name)"'
```

## Primitives

### Get "me" (sanity check auth)

```bash
curl -sS "https://api.trello.com/1/members/me?key=$TRELLO_KEY&token=$TRELLO_TOKEN" | jq -r '.username'
```

If this prints your username, auth works.

### List boards

```bash
curl -sS "https://api.trello.com/1/members/me/boards?key=$TRELLO_KEY&token=$TRELLO_TOKEN&fields=name,url" | jq -r '.[] | "\(.id)\t\(.name)\t\(.url)"'
```

### List workspaces

```bash
curl -sS "https://api.trello.com/1/members/me/organizations?key=$TRELLO_KEY&token=$TRELLO_TOKEN&fields=displayName" | jq -r '.[] | "\(.id)\t\(.displayName)"'
```

### Create board

```bash
curl -sS -X POST \
  "https://api.trello.com/1/boards/?key=$TRELLO_KEY&token=$TRELLO_TOKEN&name=$(printf '%s' "$BOARD_NAME" | jq -sRr @uri)&defaultLists=false" \
  | jq -r '{id, url}'
```

Always pass `defaultLists=false` - Trello's defaults ("To Do / Doing / Done") aren't usually what the dev wants, and we'll create lists explicitly.

Optional params:
- `idOrganization=$WORKSPACE_ID` - put the board in a workspace
- `desc=...` - board description
- `prefs_permissionLevel=private|org|public` - default is private

### Create list

```bash
curl -sS -X POST \
  "https://api.trello.com/1/boards/$BOARD_ID/lists?key=$TRELLO_KEY&token=$TRELLO_TOKEN&name=$(printf '%s' "$LIST_NAME" | jq -sRr @uri)&pos=bottom" \
  | jq -r '.id'
```

`pos` can be `top`, `bottom`, or a number. For scaffolding, create lists in order with `pos=bottom` so they stack left-to-right.

### Get lists on a board

```bash
curl -sS "https://api.trello.com/1/boards/$BOARD_ID/lists?key=$TRELLO_KEY&token=$TRELLO_TOKEN&fields=name" | jq -r '.[] | "\(.id)\t\(.name)"'
```

### Create card

```bash
curl -sS -X POST \
  "https://api.trello.com/1/cards?key=$TRELLO_KEY&token=$TRELLO_TOKEN&idList=$LIST_ID&name=$(printf '%s' "$CARD_NAME" | jq -sRr @uri)&desc=$(printf '%s' "$CARD_DESC" | jq -sRr @uri)" \
  | jq -r '.id'
```

Optional params:
- `pos=top|bottom|<number>` - position in list
- `due=2026-05-01T12:00:00.000Z` - ISO 8601 due date
- `idMembers=id1,id2` - comma-separated member IDs
- `idLabels=id1,id2` - comma-separated label IDs (see gotcha below)

### Update card

```bash
curl -sS -X PUT \
  "https://api.trello.com/1/cards/$CARD_ID?key=$TRELLO_KEY&token=$TRELLO_TOKEN&name=$(printf '%s' "$NEW_NAME" | jq -sRr @uri)"
```

Any card field can be updated: `name`, `desc`, `idList` (to move between lists), `closed` (true = archive), `due`, `dueComplete`.

### Move card to different list

```bash
curl -sS -X PUT \
  "https://api.trello.com/1/cards/$CARD_ID?key=$TRELLO_KEY&token=$TRELLO_TOKEN&idList=$TARGET_LIST_ID"
```

### Archive card

```bash
curl -sS -X PUT \
  "https://api.trello.com/1/cards/$CARD_ID?key=$TRELLO_KEY&token=$TRELLO_TOKEN&closed=true"
```

Use archive, not delete. Deleting is irreversible and rarely what the dev wants.

### Create label

```bash
curl -sS -X POST \
  "https://api.trello.com/1/boards/$BOARD_ID/labels?key=$TRELLO_KEY&token=$TRELLO_TOKEN&name=$(printf '%s' "$LABEL_NAME" | jq -sRr @uri)&color=$COLOR" \
  | jq -r '.id'
```

Valid colors: `green`, `yellow`, `orange`, `red`, `purple`, `blue`, `sky`, `lime`, `pink`, `black`, `null` (no color).

### Apply label to card

Easiest way - pass `idLabels` at card creation time as comma-separated string in the query:

```bash
curl -sS -X POST \
  "https://api.trello.com/1/cards?key=$TRELLO_KEY&token=$TRELLO_TOKEN&idList=$LIST_ID&name=...&idLabels=$LABEL_ID_1,$LABEL_ID_2"
```

Or add to existing card (one at a time):

```bash
curl -sS -X POST \
  "https://api.trello.com/1/cards/$CARD_ID/idLabels?key=$TRELLO_KEY&token=$TRELLO_TOKEN&value=$LABEL_ID"
```

### Add checklist to card

Checklists need two steps - create the checklist, then add items.

```bash
CHECKLIST_ID=$(curl -sS -X POST \
  "https://api.trello.com/1/checklists?key=$TRELLO_KEY&token=$TRELLO_TOKEN&idCard=$CARD_ID&name=$(printf '%s' "$CHECKLIST_NAME" | jq -sRr @uri)" \
  | jq -r '.id')
```

```bash
curl -sS -X POST \
  "https://api.trello.com/1/checklists/$CHECKLIST_ID/checkItems?key=$TRELLO_KEY&token=$TRELLO_TOKEN&name=$(printf '%s' "$ITEM_NAME" | jq -sRr @uri)"
```

## Recipe: scaffold a board from a spec

the dev will give you a spec as plain text or markdown. Parse it, then:

1. If he mentioned a workspace, find its ID via `members/me/organizations` and match by name (case-insensitive)
2. Create the board with `defaultLists=false`
3. Create each list in order, capturing IDs
4. Create any labels he mentioned, capturing IDs
5. For each card: create it in the right list with the right labels/description
6. Report back with the board URL

**Before starting**, show the dev what you parsed from the spec and confirm:

> Got it. Here's what I'll create:
> - Board: "Shroomshire Restoration" (in workspace "Tabs Labs")
> - Lists: Backlog, In Progress, Review, Done
> - Labels: bug (red), feature (green), art (purple)
> - 12 cards across Backlog
>
> Proceed?

This matters because scaffolding is irreversible in any practical sense - if labels or lists are wrong, the dev has to clean them up manually. Confirm before committing.

If the dev gives a file path (e.g. `PROJECT.md`), read it first with `cat` or the Read tool.

## Recipe: bulk card creation

Given a list of card names (or a markdown list), create all of them in the same list.

Loop with a small sleep to stay under rate limits:

```bash
for card in "Card 1" "Card 2" "Card 3"; do
  curl -sS -X POST \
    "https://api.trello.com/1/cards?key=$TRELLO_KEY&token=$TRELLO_TOKEN&idList=$LIST_ID&name=$(printf '%s' "$card" | jq -sRr @uri)" \
    | jq -r '.id'
  sleep 0.1
done
```

One curl call per card. Don't try to batch in a single request - the API doesn't support it.

## Recipe: bulk move or update

Same pattern - get the card IDs first (from a list or board), then loop with PUT requests. Show the dev the plan before executing on large batches (10+ cards).

## Recipe: mirror markdown checklist to cards

If the dev hands you markdown like:

```markdown
## Backlog
- [ ] Set up Supabase schema
- [ ] Design landing page
- [ ] Write privacy policy

## In Progress
- [ ] Implement auth flow
```

Parse the `##` headings as list names, and each `- [ ]` item as a card in that list. Confirm the plan, then scaffold.

## Gotchas

- **idLabels formatting**: pass as a plain comma-separated string in the query (`idLabels=abc123,def456`), NOT as a JSON array. The JSON array form returns 400. Reference: community.developer.atlassian.com thread on this.
- **URL encoding**: card names with `&`, `=`, `#`, spaces, or emoji MUST be URL-encoded. Use `jq -sRr @uri` - it handles Unicode correctly.
- **Token scope**: the token the dev generates from the Power-Up admin page has full account access. It can read/write every board he's on. Treat the token as a password.
- **Deleted cards are gone**: `DELETE /cards/{id}` is permanent. Prefer `closed=true` (archive) unless the dev explicitly says "delete permanently".
- **Short board IDs work**: the 8-char code from the URL (`dQHqCohZ`) is accepted anywhere a board ID is needed.
- **"me" shortcut**: use `members/me` instead of looking up your own member ID.
- **Rate limits**: you likely won't hit them for normal use, but for scaffolding 50+ cards add `sleep 0.1` between calls.
- **defaultLists=true creates "To Do / Doing / Done"**: always pass `defaultLists=false` when creating a board so you control the list structure.

## Trello-specific rules

- Piping curl output to `jq` is fine (not considered chaining). All other shell rules follow global CLAUDE.md.
- Never commit the dev's env or any file containing his token.

## When to ask

Always confirm before:
- Creating a new board (irreversible cleanup if wrong)
- Bulk-creating 10+ cards
- Bulk-updating existing cards
- Deleting anything (and prefer archive)
- Writing to a board the dev didn't explicitly name in this session

Never ask for:
- The API key/token (read from env only)
- Which board when the dev explicitly named one

## Output format

After any successful operation, report concisely:

> Created board "Shroomshire Restoration": https://trello.com/b/abc123
> - 4 lists, 3 labels, 12 cards

Not a wall of IDs. the dev wants the URL and a summary.
