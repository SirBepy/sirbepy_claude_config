---
name: shortcut-priorities
description: Pulls the dev's Shortcut notification/activity feed over a lookback window, groups it by ticket, reads full ticket + comment threads for anything actionable, and returns a prioritized "what to work on" list. Report-only, never comments or changes ticket state.
disable-model-invocation: true
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
- `Agent` (`general-purpose`, model `sonnet`) - only if the candidate-ticket count exceeds the dispatch-volume gate in step 5. Otherwise do the ticket reads inline.

## Auth — two different credentials, don't confuse them

1. **Private activity endpoint** (`POST https://app.shortcut.com/backend/api/private/permission/activity`) — needs Joe's browser **session cookie** (`sid=...`), plus `tenant-organization2` / `tenant-workspace2` headers. The public API token does **not** work here: confirmed 2026-07-30, both `shortcut-token` and `Shortcut-Token` return `403 user_denied_access` while the same token returns `200` on `/api/v3/member`. Don't re-test, don't ask Joe for a different token.
   - Cookie + tenant IDs are cached in `~/.claude/.env` as `SHORTCUT_SID`, `SHORTCUT_TENANT_ORG`, `SHORTCUT_TENANT_WS` (added 2026-07-30 at Joe's explicit request). **Always try the cached values first** — no need to ask him for anything.
   - Tenant IDs are stable. Only `SHORTCUT_SID` expires. If the first call returns `403` / `401` / `"tag":"...unauthorized"`, THEN ask Joe for a fresh one: open Shortcut → DevTools → Network → reload the Stories view → right-click the `activity` request → Copy as cURL → paste. Extract the `sid=` value, overwrite `SHORTCUT_SID` in `~/.claude/.env`, retry.
   - `"tag":"organization2_missing"` is NOT an expired cookie — it means the tenant headers didn't reach the server (usually a broken env extraction). Fix the extraction, don't ask Joe.
   - Env extraction gotcha: a `grep` pattern anchored with `^` plus literal `\xEF\xBB\xBF` BOM bytes silently matches nothing inside double quotes. Use the unanchored form: `grep -i "SHORTCUT_SID=" "$ENV" | sed 's/^.*SHORTCUT_SID=//' | sed 's/\xEF\xBB\xBF//g' | tr -d '\r\n'`.
2. **Public v3 API** (`api.app.shortcut.com/api/v3`) - the durable `SHORTCUT_API_TOKEN` in `~/.claude/.env` (has a BOM - strip it, see extraction pattern below). Used for the full-ticket-detail pass in step 4. Fine to use freely, no need to re-ask each run.

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

### 0. Liveness probe - verify SHORTCUT_SID before committing to the full run

One cheap call against the private activity endpoint, before paginating, so a dead cookie surfaces immediately instead of after burning a failed page fetch (or mid-loop, if it expires between calls).

```python
import json, urllib.request, urllib.error

COOKIE = 'sid=...'   # cached SHORTCUT_SID from ~/.claude/.env
ORG    = '...'       # cached SHORTCUT_TENANT_ORG
WS     = '...'       # cached SHORTCUT_TENANT_WS
before = '<recent-known-good-ISO-timestamp>'   # last `end` you've seen, never a computed "now"

req = urllib.request.Request(
    'https://app.shortcut.com/backend/api/private/permission/activity',
    data=json.dumps({'before': before}).encode('utf-8'),
    headers={
        'accept': '*/*', 'content-type': 'application/json; charset=UTF-8',
        'tenant-organization2': ORG, 'tenant-workspace2': WS,
        'x-requested-with': 'XMLHttpRequest', 'cookie': COOKIE,
    },
    method='POST',
)
try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        probe_body = resp.read().decode('utf-8')
except urllib.error.HTTPError as e:
    if e.code in (401, 403):
        print('SHORTCUT_SID is dead. Refresh it:')
        print('  Shortcut -> DevTools -> Network -> reload the Stories view -> right-click the `activity` request -> Copy as cURL')
        print('  Extract the sid= value, overwrite SHORTCUT_SID in ~/.claude/.env, retry.')
        raise SystemExit(1)
    raise   # any other status: read it, don't retry blindly (see Step 2)
```

`probe_body` is itself page 1 of the activity feed - hand it straight to Step 2's loop as the first iteration instead of re-fetching.

### 2. Paginate the private activity feed

The endpoint pages **backwards in time** via a `before` cursor. Each response returns `{start, end, data}` - `start` is the earliest timestamp in that page; feed it back in as the next `before`. `before` must not be in the future (server 400s with `"Can not set timestamp to future time."` - seed the first call with a known-good recent timestamp, e.g. the last `end` you've seen, not a computed "now"). Python, not bash - ports the loop that used to live here exactly, edge case for edge case:

```python
import json, os, urllib.request, urllib.error

os.makedirs('C:/tmp/shortcut_notif', exist_ok=True)
cutoff = '<today - lookback_days, ISO>'
i = 0
while True:
    i += 1
    req = urllib.request.Request(
        'https://app.shortcut.com/backend/api/private/permission/activity',
        data=json.dumps({'before': before}).encode('utf-8'),
        headers={
            'accept': '*/*', 'content-type': 'application/json; charset=UTF-8',
            'tenant-organization2': ORG, 'tenant-workspace2': WS,
            'x-requested-with': 'XMLHttpRequest', 'cookie': COOKIE,
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        open(f'C:/tmp/shortcut_notif/page_{i}.json', 'w', encoding='utf-8').write(body)
        print(f'HTTP {e.code} on page {i}: {body[:500]}')   # error - surface the raw response to Joe, don't retry blindly
        break

    open(f'C:/tmp/shortcut_notif/page_{i}.json', 'w', encoding='utf-8').write(body)
    data = json.loads(body)
    start = data.get('start')
    if not start:            # empty - stop, surface the raw response to Joe
        break
    if start < cutoff:
        break
    before = start
    if i > 60:                # safety stop
        break
```

If the very first call errors, don't retry blindly - read the error (`page_1.json`). A `"Can not set timestamp to future time"` means the seed timestamp was bad, not that the cookie is dead (that's what Step 0 already ruled out).

### 3. Dedupe + group by ticket (python, not jq - not installed)

Merge all `data[]` arrays, dedupe by event `id`, then group by the story each event is actually about: prefer an `actions[].entity_type == "story"` entry (its `id`/`name`/`app_url`), fall back to a `references[].entity_type == "story"` entry, fall back to `primary_id` if it's an int. Skip events with no resolvable story (workspace-level bulk-update noise, reactions on entities you can't resolve, etc.).

Per ticket, track: `reasons` (union across events — `mention`, `assignment`, `author`, `follower`, `group-assignment-*`), comment events (`entity_type=="story-comment", action=="create"`, with `mention_ids` telling you if Joe was `@`-mentioned in that specific comment), and last-activity timestamp. `PYTHONIOENCODING=utf-8` is required on this Windows setup — comment text contains emoji that break the default `cp1250` console encoding otherwise.

### 4. Filter to candidates worth reading, then pull full ticket + comments (public API)

Not every grouped ticket needs a deep read. Skip tickets whose only reasons are `follower`/`group-assignment-*` with zero comments — that's pure board-hygiene noise. Candidates worth a full read: any ticket with `mentions > 0` OR `comments > 0` from someone other than Joe.

**Then drop every candidate in an off-Joe's-plate state: the two `done` states plus Ready for deploy.** Resolve all three ids from `~/.claude/refs/shortcut-api.md`'s state list, same as every other id in this skill; do not inline the numbers here. Note that Ready for deploy is classed `started` there, not `done`: this filter deliberately treats it as finished anyway. Joe's rule, 2026-08-25: once a ticket reaches Ready for deploy it is out of his hands, so late QA pushback on it is not his queue. Drop it silently, no FYI line. This is a hard filter applied BEFORE ranking, so such a ticket can never surface as a tier-1 regression no matter how recent or how pointed the comment is.

**One carve-out, and only this one:** if a dropped ticket's comments ask Joe to do something OUTSIDE that ticket that has no evidence of having happened (most often "can you file a follow-up ticket for this"), surface it. That is new work landing on him, not a status alert about a ticket he is done with, so his rule above does not cover it. One line, no tier.

For each candidate:
```bash
curl -s "https://api.app.shortcut.com/api/v3/stories/<id>" -H "Shortcut-Token: $TOKEN" > story_<id>.json
```
Check `completed`, `started`, `blocked`, `workflow_state_id`, and read the full `comments[]` (the activity feed truncates text). This is what tells you whether the thread is actually still open — e.g. Joe already replied after the last mention, or the ticket completed since the mention was posted.

### 5. Dispatch-volume gate

- **≤ 10 candidate tickets:** read them inline (as above).
- **> 10:** fan out one `general-purpose` agent per ticket (or batches of 2-3), `model: 'sonnet'`, single message multiple `Agent` calls. Paste the canonical preamble from `refs/builder-preamble.md` into each dispatch prompt (it's read-only, so the `READ-ONLY DISPATCH` opt-out applies) - `hooks/dispatch-preamble-guard.py` rejects a prompt missing its markers. Each dispatch only needs the ticket ID + the public API token pattern above (never the session cookie - it's not needed past step 2). Ask each to return: last commenter, is it Joe, is there an unanswered direct question/QA rejection, current workflow state, one-line verdict.

### 6. Cross-reference with real code state before calling something "still open"

A QA comment or rejected fix can be stale - check git across all four ZNG repos before flagging (a same-day fix commonly lands in `zng-admin` or `zng-biller`, not just `zng-app`):

```bash
for repo in C:/Users/tecno/Desktop/Projects/zng-app C:/Users/tecno/Desktop/Projects/zng-admin C:/Users/tecno/Desktop/Projects/zng-api C:/Users/tecno/Desktop/Projects/zng-biller; do
  git -C "$repo" log --oneline -10 --grep="<ticket-id>"
done
```
and compare commit timestamps against the comment timestamp. A same-day-or-later commit whose message plausibly addresses the QA feedback means "likely already fixed, worth a re-verify ping" rather than "untouched." Don't assume — read the commit's diff/subject before downgrading a finding.

### 7. Synthesize the prioritized report

Rank by actual urgency, not recency:

Everything still standing is on Joe's plate (step 4 already dropped Complete, Won't do and Ready for deploy).

1. **Commitments Joe made** - he replied with a date or a "will do" and the work has no commit yet. Highest priority: someone is expecting it on a stated day.
2. **Regressions / QA-rejected fixes on things Joe shipped** - a mention saying "this doesn't meet the requirement" or "still reproduces" on a ticket Joe owns/authored, on a ticket step 4 did not drop.
3. **Direct blocking questions** - someone asked Joe something specific and can't proceed without an answer (design clarification, "where is X used").
4. **Bugs found on active/in-flight epics** - QA-reported bugs on tickets currently In Progress/PR Review/Testing that Joe owns.
5. **Long-open unresolved threads** - real back-and-forth that's been open a while with no resolution, lower urgency but worth closing out.

There is no FYI tier. A ticket that is finished, answered, or someone else's call does not get a line, with the single step-4 carve-out above (a dangling request to do something outside the ticket) as the only exception.

For every item: ticket id + title + link, one-line summary of what's being asked, and why it's ranked where it is (unanswered since when / regression on which commit / etc).

## What this skill never does

- Never posts a comment or changes ticket/workflow state — report only, same rule as the rest of this skill family: no ticket mutation without explicit go-ahead, and never draft-and-post a comment in the same step.
- Never writes the session cookie into this skill file, a memory file, or a scratch script — `~/.claude/.env` is the one allowed home for it.
- Never treats the activity feed's truncated comment snippet as ground truth — always re-read the full comment via the public API before calling something unresolved.
- Never assumes a QA-reported issue is still live without checking git for a same-day-or-later fix commit first.
