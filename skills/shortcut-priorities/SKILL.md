---
name: shortcut-priorities
description: Triggers on /shortcut-priorities only. Pulls Joe's Shortcut notification/activity feed over a lookback window, groups it by ticket, reads full ticket + comment threads for anything actionable, and returns a prioritized "what to work on" list. Report-only — never comments or changes ticket state.
argument-hint: "[lookback_days]"
---

# /shortcut-priorities

> Joe's stand-in for Shortcut's notification bell (there's no public "notifications" endpoint in Shortcut's REST API — the private activity feed below is the closest substitute). Pulls the private activity feed, groups by ticket, and tells Joe what actually needs a response vs what's just noise.

## Why this skill exists

- Shortcut's public REST API (`api.app.shortcut.com/api/v3`) has no notifications/activity endpoint. The only place that data lives is the private, session-cookie-authenticated endpoint the web app itself calls.
- A raw activity feed is mostly noise — group-assignment churn, follower adds, bot/system events. The signal is: who's waiting on Joe (a `@mention`, a direct question in a comment, QA pushback on something Joe shipped) grouped per ticket, not a flat chronological list.
- Figuring out what's actually still-open requires reading the real ticket (workflow state, full comment thread, whether Joe already replied) — not just the activity-feed snippet, which is truncated and reason-coded but not verdict-bearing.

## Args

```
/shortcut-priorities [lookback_days]
```

- `lookback_days` (optional) — how far back to paginate the activity feed. Default: `10`.

## Required tools

- `Bash` — curl against both the private activity endpoint and the public v3 API; python for JSON grouping (no `jq` in this environment — confirmed absent, use python).
- `Agent` (`general-purpose`, model `sonnet`) — only if the candidate-ticket count exceeds the dispatch-volume gate in step 4. Otherwise do the ticket reads inline.

## Auth — two different credentials, don't confuse them

1. **Private activity endpoint** (`POST https://app.shortcut.com/backend/api/private/permission/activity`) — needs Joe's browser **session cookie** (`sid=...`), plus `tenant-organization2` / `tenant-workspace2` headers. The public API token does **not** work here: confirmed 2026-07-30, both `shortcut-token` and `Shortcut-Token` return `403 user_denied_access` while the same token returns `200` on `/api/v3/member`. Don't re-test, don't ask Joe for a different token.
   - Cookie + tenant IDs are cached in `~/.claude/.env` as `SHORTCUT_SID`, `SHORTCUT_TENANT_ORG`, `SHORTCUT_TENANT_WS` (added 2026-07-30 at Joe's explicit request). **Always try the cached values first** — no need to ask him for anything.
   - Tenant IDs are stable. Only `SHORTCUT_SID` expires. If the first call returns `403` / `401` / `"tag":"...unauthorized"`, THEN ask Joe for a fresh one: open Shortcut → DevTools → Network → reload the Stories view → right-click the `activity` request → Copy as cURL → paste. Extract the `sid=` value, overwrite `SHORTCUT_SID` in `~/.claude/.env`, retry.
   - `"tag":"organization2_missing"` is NOT an expired cookie — it means the tenant headers didn't reach the server (usually a broken env extraction). Fix the extraction, don't ask Joe.
   - Env extraction gotcha: a `grep` pattern anchored with `^` plus literal `\xEF\xBB\xBF` BOM bytes silently matches nothing inside double quotes. Use the unanchored form: `grep -i "SHORTCUT_SID=" "$ENV" | sed 's/^.*SHORTCUT_SID=//' | sed 's/\xEF\xBB\xBF//g' | tr -d '\r\n'`.
2. **Public v3 API** (`api.app.shortcut.com/api/v3`) — the durable `SHORTCUT_API_TOKEN` in `~/.claude/.env` (has a BOM — strip it, see extraction pattern below). Used for the full-ticket-detail pass in step 3. Fine to use freely, no need to re-ask each run.

```bash
python -c "
with open(r'C:/Users/tecno/.claude/.env', 'rb') as f:
    content = f.read().decode('utf-8-sig')
for line in content.splitlines():
    if line.startswith('SHORTCUT_API_TOKEN='):
        print(line.split('=',1)[1].strip())
"
```

## Fixed identity & constants

Dev UUID, mention name, and workflow-state IDs: see `~/.claude/refs/shortcut-api.md`.

- Scratch dir: `C:/tmp/shortcut_notif/` — ephemeral, fine to overwrite/clean each run.

## Flow

### 1. Paginate the private activity feed

The endpoint pages **backwards in time** via a `before` cursor. Each response returns `{start, end, data}` — `start` is the earliest timestamp in that page; feed it back in as the next `before`. `before` must not be in the future (server 400s with `"Can not set timestamp to future time."` — seed the first call with a known-good recent timestamp, e.g. the last `end` you've seen, not a computed "now").

```bash
COOKIE='sid=...'          # from Joe's pasted request, this run only
ORG='...'                 # tenant-organization2
WS='...'                  # tenant-workspace2
before="<recent-known-good-ISO-timestamp>"
CUTOFF="<today - lookback_days, ISO>"
i=0
while true; do
  i=$((i+1))
  resp=$(curl -s -X POST 'https://app.shortcut.com/backend/api/private/permission/activity' \
    -H 'accept: */*' -H 'content-type: application/json; charset=UTF-8' \
    -H "tenant-organization2: $ORG" -H "tenant-workspace2: $WS" \
    -H 'x-requested-with: XMLHttpRequest' -H "cookie: $COOKIE" \
    -d "{\"before\":\"$before\"}")
  echo "$resp" > "C:/tmp/shortcut_notif/page_$i.json"
  start=$(echo "$resp" | grep -o '"start":"[^"]*"' | head -1 | cut -d'"' -f4)
  [ -z "$start" ] && break        # error/empty — stop, surface the raw response to Joe
  [[ "$start" < "$CUTOFF" ]] && break
  before="$start"
  [ $i -gt 60 ] && break          # safety stop
done
```

If the very first call errors, don't retry blindly — read the error (`page_1.json`). A `"Can not set timestamp to future time"` means the seed timestamp was bad, not that the cookie is dead.

### 2. Dedupe + group by ticket (python, not jq — not installed)

Merge all `data[]` arrays, dedupe by event `id`, then group by the story each event is actually about: prefer an `actions[].entity_type == "story"` entry (its `id`/`name`/`app_url`), fall back to a `references[].entity_type == "story"` entry, fall back to `primary_id` if it's an int. Skip events with no resolvable story (workspace-level bulk-update noise, reactions on entities you can't resolve, etc.).

Per ticket, track: `reasons` (union across events — `mention`, `assignment`, `author`, `follower`, `group-assignment-*`), comment events (`entity_type=="story-comment", action=="create"`, with `mention_ids` telling you if Joe was `@`-mentioned in that specific comment), and last-activity timestamp. `PYTHONIOENCODING=utf-8` is required on this Windows setup — comment text contains emoji that break the default `cp1250` console encoding otherwise.

### 3. Filter to candidates worth reading, then pull full ticket + comments (public API)

Not every grouped ticket needs a deep read. Skip tickets whose only reasons are `follower`/`group-assignment-*` with zero comments — that's pure board-hygiene noise. Candidates worth a full read: any ticket with `mentions > 0` OR `comments > 0` from someone other than Joe.

For each candidate:
```bash
curl -s "https://api.app.shortcut.com/api/v3/stories/<id>" -H "Shortcut-Token: $TOKEN" > story_<id>.json
```
Check `completed`, `started`, `blocked`, `workflow_state_id`, and read the full `comments[]` (the activity feed truncates text). This is what tells you whether the thread is actually still open — e.g. Joe already replied after the last mention, or the ticket completed since the mention was posted.

### 4. Dispatch-volume gate

- **≤ 10 candidate tickets:** read them inline (as above).
- **> 10:** fan out one `general-purpose` agent per ticket (or batches of 2-3), `model: 'sonnet'`, single message multiple `Agent` calls. Each dispatch only needs the ticket ID + the public API token pattern above (never the session cookie — it's not needed past step 1). Ask each to return: last commenter, is it Joe, is there an unanswered direct question/QA rejection, current workflow state, one-line verdict.

### 5. Cross-reference with real code state before calling something "still open"

A QA comment or rejected fix can be stale — check git before flagging:

```bash
git -C C:/Users/tecno/Desktop/Projects/zng-app log --oneline -10 --grep="<ticket-id>"
```
and compare commit timestamps against the comment timestamp. A same-day-or-later commit whose message plausibly addresses the QA feedback means "likely already fixed, worth a re-verify ping" rather than "untouched." Don't assume — read the commit's diff/subject before downgrading a finding.

### 6. Synthesize the prioritized report

Rank by actual urgency, not recency:

1. **Regressions / QA-rejected fixes on things Joe shipped** — a mention saying "this doesn't meet the requirement" or "still reproduces" on a ticket Joe owns/authored. Highest priority — someone is blocked re-verifying Joe's own work.
2. **Direct blocking questions** — someone asked Joe something specific and can't proceed without an answer (design clarification, "where is X used").
3. **Bugs found on active/in-flight epics** — QA-reported bugs on tickets currently In Progress/PR Review/Testing that Joe owns.
4. **Long-open unresolved threads** — real back-and-forth that's been open a while with no resolution, lower urgency but worth closing out.
5. **FYI/no-action** — "live in dev" info comments, reactions, already-`Complete`/`Won't do` tickets, pure board-hygiene events. Mention only if something dangling depends on them (e.g. someone asked Joe to file a follow-up ticket and it's unclear whether that happened).

For each item in tiers 1-4: ticket id + title + link, one-line summary of what's being asked, and why it's ranked where it is (unanswered since when / regression on which commit / etc).

## What this skill never does

- Never posts a comment or changes ticket/workflow state — report only, same rule as the rest of this skill family: no ticket mutation without explicit go-ahead, and never draft-and-post a comment in the same step.
- Never writes the session cookie into this skill file, a memory file, or a scratch script — `~/.claude/.env` is the one allowed home for it.
- Never treats the activity feed's truncated comment snippet as ground truth — always re-read the full comment via the public API before calling something unresolved.
- Never assumes a QA-reported issue is still live without checking git for a same-day-or-later fix commit first.
