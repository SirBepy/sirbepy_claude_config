---
name: shortcut-priorities
description: Pulls the dev's Shortcut notification/activity feed over a lookback window, groups it by ticket, reads full ticket + comment threads for anything actionable, and returns a prioritized "what to work on" list. Report-only, never comments or changes ticket state.
disable-model-invocation: true
argument-hint: "[lookback_days] [free text, e.g. what can we work on]"
---

# /shortcut-priorities

> Joe's stand-in for Shortcut's notification bell (there's no public "notifications" endpoint in Shortcut's REST API — the private activity feed below is the closest substitute). Pulls the private activity feed, groups by ticket, and tells Joe what actually needs a response vs what's just noise.

## Why this skill exists

- Shortcut's public REST API (`api.app.shortcut.com/api/v3`) has no notifications/activity endpoint. The only place that data lives is the private, session-cookie-authenticated endpoint the web app itself calls.
- A raw activity feed is mostly noise — group-assignment churn, follower adds, bot/system events. The signal is: who's waiting on Joe (a `@mention`, a direct question in a comment, QA pushback on something Joe shipped) grouped per ticket, not a flat chronological list.
- Figuring out what's actually still-open requires reading the real ticket (workflow state, full comment thread, whether Joe already replied) — not just the activity-feed snippet, which is truncated and reason-coded but not verdict-bearing.

## Args

```
/shortcut-priorities [lookback_days] [free text]
```

- `lookback_days` (optional) — how far back to paginate the activity feed. Default: `10`.
- free text (optional) - when it reads as "what can we work on" / "anything for me to pick up" / "what's next", the report also carries the workable-now section from step 7. Without it the report covers only who is waiting on a reply.

## Required tools

- `Bash` — curl against both the private activity endpoint and the public v3 API; python for JSON grouping (no `jq` in this environment — confirmed absent, use python).
- `Agent` (`general-purpose`, model `sonnet`) - only if the candidate-ticket count exceeds the dispatch-volume gate in step 5. Otherwise do the ticket reads inline.

## Auth — two different credentials, don't confuse them

1. **Private activity endpoint** (`POST https://app.shortcut.com/backend/api/private/permission/activity`) — needs Joe's browser **session cookie** (`sid=...`), plus `tenant-organization2` / `tenant-workspace2` headers. The public API token does **not** work here: confirmed 2026-07-30, both `shortcut-token` and `Shortcut-Token` return `403 user_denied_access` while the same token returns `200` on `/api/v3/member`. Don't re-test, don't ask Joe for a different token.
   - Cookie + tenant IDs are cached in `~/.claude/.env` as `SHORTCUT_SID`, `SHORTCUT_TENANT_ORG`, `SHORTCUT_TENANT_WS` (added 2026-07-30 at Joe's explicit request). **Always try the cached values first** — no need to ask him for anything.
   - Tenant IDs are stable. Only `SHORTCUT_SID` expires. A `401` / `403` is not proof the cookie is dead: the server returns the same `401 {"tag":"profile_invalid"}` for an expired cookie and for a valid cookie on a request that does not look like the browser's (missing `origin` / `referer` / `user-agent` / page headers). So a `401` / `403` / `"tag":"...unauthorized"` first gets one retry with the full browser header set from Step 0. Only if that retry also fails, ask Joe for a fresh one: open Shortcut → DevTools → Network → reload the Stories view → right-click the `activity` request → Copy as cURL → paste. Extract the `sid=` value, overwrite `SHORTCUT_SID` in `~/.claude/.env`, retry.
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

The request carries the full header set a browser sends. A trimmed set (only `accept`, `content-type`, the two tenant headers, `x-requested-with`, `cookie`) returned `401 profile_invalid` on 2026-10-19 while the same cookie succeeded over `curl` with the browser's `origin`, `referer`, `user-agent`, `clubhouse-page` and `shortcut-action-context` added. Those five were confirmed together, never narrowed to the load-bearing subset, so send all five.

```python
import json, time, urllib.request, urllib.error

COOKIE = 'sid=...'   # cached SHORTCUT_SID from ~/.claude/.env
ORG    = '...'       # cached SHORTCUT_TENANT_ORG
WS     = '...'       # cached SHORTCUT_TENANT_WS
before = '<recent-known-good-ISO-timestamp>'   # last `end` you've seen, never a computed "now"

# Full browser header set, reused verbatim by Step 2.
HEADERS = {
    'accept': '*/*', 'content-type': 'application/json; charset=UTF-8',
    'tenant-organization2': ORG, 'tenant-workspace2': WS,
    'x-requested-with': 'XMLHttpRequest', 'cookie': COOKIE,
    'origin': 'https://app.shortcut.com',
    'referer': 'https://app.shortcut.com/zirtue/',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
    'clubhouse-page': 'stories', 'shortcut-action-context': 'stories',
}

def fetch_page(before):
    req = urllib.request.Request(
        'https://app.shortcut.com/backend/api/private/permission/activity',
        data=json.dumps({'before': before}).encode('utf-8'),
        headers=HEADERS,
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode('utf-8')

for attempt in (1, 2):
    try:
        probe_body = fetch_page(before)
        break
    except urllib.error.HTTPError as e:
        if e.code in (401, 403) and attempt == 1:
            time.sleep(2)   # one retry with the same full header set before believing the cookie is dead
            continue
        if e.code in (401, 403):
            print(f'HTTP {e.code} twice with the full browser header set: {e.read().decode("utf-8")[:300]}')
            print('SHORTCUT_SID is dead. Refresh it:')
            print('  Shortcut -> DevTools -> Network -> reload the Stories view -> right-click the `activity` request -> Copy as cURL')
            print('  Extract the sid= value, overwrite SHORTCUT_SID in ~/.claude/.env, retry.')
            raise SystemExit(1)
        raise   # any other status: read it, don't retry blindly (see Step 2)
```

A `401` / `403` (any `tag`, `profile_invalid` included) from this probe is proof of a dead cookie only when the request carried every header in `HEADERS`. A request built any other way (a trimmed header dict, a bare `curl`, another client) that gets a 401 does not count: re-send it with `HEADERS` first, and ask Joe for a fresh cookie only if that retry also fails. Never ask on a first 401.

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
        headers=HEADERS,   # the full browser header set defined in Step 0, never a trimmed copy
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

If the very first call errors, don't retry blindly - read the error (`page_1.json`). A `"Can not set timestamp to future time"` means the seed timestamp was bad, not that the cookie is dead (that's what Step 0 already ruled out). A `401` / `403` mid-loop gets the same single retry with `HEADERS` as Step 0 before it is reported as an expired cookie.

### 3. Dedupe + group by ticket (python, not jq - not installed)

Merge all `data[]` arrays, dedupe by event `id`, then group by the story each event is actually about: prefer an `actions[].entity_type == "story"` entry (its `id`/`name`/`app_url`), fall back to a `references[].entity_type == "story"` entry, fall back to `primary_id` if it's an int. Skip events with no resolvable story (workspace-level bulk-update noise, reactions on entities you can't resolve, etc.).

Per ticket, track: `reasons` (union across events — `mention`, `assignment`, `author`, `follower`, `group-assignment-*`), comment events (`entity_type=="story-comment", action=="create"`, with `mention_ids` telling you if Joe was `@`-mentioned in that specific comment), and last-activity timestamp. `PYTHONIOENCODING=utf-8` is required on this Windows setup — comment text contains emoji that break the default `cp1250` console encoding otherwise.

### 3a. Feed-lag check

Record the newest event timestamp across all pages (read the timestamp key off an event in `page_1.json` rather than assuming its name; page 1's `end` is the fallback). If it is more than ~1h older than now, the report opens with one line: `Feed lags by <X>h: mentions after <newest-ts> come from the search pass only.` Print the newest-event timestamp itself in the report every run, lag or not, so a gap is never silent.

Observed 2026-10-16: with `before = now - 10min`, the newest event returned was about 4h old, and a comment in the story's own `comments[]` and an @-mention newer than that never appeared in the feed. Whether that is server lag or the `before` cursor behaving differently from what Step 2 assumes is not established. Treat the feed as possibly stale and let step 3b cover the gap.

### 3b. Public search pass (independent of the feed)

The feed only shows tickets that generated an event for Joe, so it misses fresh @-mentions during a lag, and it never shows his own queue. Run two `search/stories` queries (recipe, operators and pagination in `~/.claude/refs/shortcut-api.md` "Searching stories"; `detail=full` returns comments in the same response). Public token only, no session cookie.

```python
import json, os, urllib.parse, urllib.request

# Same BOM-safe read as the Auth section; the token stays in memory, never in a file.
with open(r'C:/Users/tecno/.claude/.env', 'rb') as f:
    env_lines = f.read().decode('utf-8-sig').splitlines()
TOKEN = next(l.split('=', 1)[1].strip() for l in env_lines if l.startswith('SHORTCUT_API_TOKEN='))
API = 'https://api.app.shortcut.com'
JOE_UUID = '<dev UUID from refs/shortcut-api.md>'
OWN_QUEUE_STATES = {'<To Do id>', '<In Progress id>', '<Testing id>'}   # resolve from refs/shortcut-api.md; the search API rejects workflow_state_ids, so filter client-side

def search(query, max_pages=40):
    url = API + '/api/v3/search/stories?' + urllib.parse.urlencode({'query': query, 'detail': 'full', 'page_size': 25})
    out = []
    for _ in range(max_pages):
        req = urllib.request.Request(url, headers={'Shortcut-Token': TOKEN})
        with urllib.request.urlopen(req, timeout=30) as resp:
            page = json.loads(resp.read().decode('utf-8'))
        out.extend(page.get('data') or [])
        if not page.get('next'):
            break
        url = API + page['next']   # `next` is a relative URL, null when exhausted
    return out

cutoff_date = '<today - lookback_days, YYYY-MM-DD>'
cutoff_iso = '<same cutoff as Step 2, ISO>'

own = [s for s in search('owner:josipmui !is:archived !is:done')
       if str(s.get('workflow_state_id')) in OWN_QUEUE_STATES]

# Open stories touched in the window, owned by anyone; keep those with a fresh comment @-mentioning Joe.
touched = search(f'!is:archived !is:done updated:{cutoff_date}..*')
mentioned = []
for s in touched:
    hits = [c for c in s.get('comments', [])
            if '@josipmui' in (c.get('text') or '')
            and c.get('author_id') != JOE_UUID
            and (c.get('created_at') or '') >= cutoff_iso]
    if hits:
        mentioned.append((s, hits))

os.makedirs('C:/tmp/shortcut_notif', exist_ok=True)
json.dump({'own': own, 'mentioned': [s for s, _ in mentioned]},
          open('C:/tmp/shortcut_notif/search_pass.json', 'w', encoding='utf-8'))
```

`updated:<date>..*` uses the same range form as `completed:<date>..*` in the refs file. If the search answers 400 to it, drop the clause and filter on each story's `updated_at` client-side instead (more pages, same result).

Dedupe by story id against the step 3 feed groups:

- `mentioned` entries join the step 4 candidate list even when the feed never returned them (the @-mention is the reason; they still go through step 4's state filter and full read).
- `own` entries are not reply candidates by themselves. They feed step 7's workable-now section, and join step 4's candidate list only when they also carry an unanswered thread from someone else.

### 4. Filter to candidates worth reading, then pull full ticket + comments (public API)

Not every grouped ticket needs a deep read. Skip tickets whose only reasons are `follower`/`group-assignment-*` with zero comments: that's pure board-hygiene noise. Candidates worth a full read: any ticket with `mentions > 0` OR `comments > 0` from someone other than Joe, plus the step 3b `mentioned` hits the feed did not return.

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

Report header, before the tiers: the feed's newest-event timestamp and, when step 3a found a lag, the lag line. Close the tier list with this boundary line, verbatim in meaning: `This covers who is waiting on a reply, not your full active queue.` A thin or empty reply-needed result must never read as "that is everything on your plate"; point to the workable-now section (or tell Joe to re-run with "what can we work on") for the queue itself.

#### Workable-now section (only when the args read as "what can we work on")

Appended after the tiers. Source: step 3b `own` plus the `mentioned` hits, each in To Do or In Progress, `blocked` false and not in the Blocked or On hold state (ids in `~/.claude/refs/shortcut-api.md`). Ready for deploy, Complete and Won't do stay excluded, same as step 4.

- Rank by the Priority custom field, Highest first, then High, Medium, Low, unset last. The pinned field id is in `skills/ticket/shortcut.md`; map each story's `value_id` to a name with `GET /api/v3/custom-fields/<Priority field id>` (`enum_values`). Only High and Medium ids are pinned there, so read Highest from that GET instead of guessing a UUID.
- Split by repo, from the Skill Set / Technical Area fields via the repo mapping table in `skills/ticket/shortcut.md` (Web App + Frontend = zng-app, Admin Portal = zng-admin, Biller Portal = zng-biller, Backend = zng-api). In a session whose cwd is one of those repos, list that repo's group first.
- A ticket owned by someone else (QA files and owns bug tickets, the dev gets only a group assignment) belongs here when a recent comment @-mentions Joe on it. Say who owns it.
- Per item: id + title + link, state, priority, owner, one line on why it is workable (mention, own queue). Run step 6's git cross-check on the top few so a ticket already fixed in a repo is not listed as untouched.

## What this skill never does

- Never posts a comment or changes ticket/workflow state — report only, same rule as the rest of this skill family: no ticket mutation without explicit go-ahead, and never draft-and-post a comment in the same step.
- Never writes the session cookie into this skill file, a memory file, or a scratch script — `~/.claude/.env` is the one allowed home for it.
- Never treats a first `401` / `403` from the private endpoint as a dead cookie: retry once with the full `HEADERS` set before asking Joe for a fresh one.
- Never treats the activity feed as complete: it can lag hours behind, so step 3b's search pass and step 3a's lag line always run.
- Never treats the activity feed's truncated comment snippet as ground truth — always re-read the full comment via the public API before calling something unresolved.
- Never assumes a QA-reported issue is still live without checking git for a same-day-or-later fix commit first.
