# Shortcut API — shared core

Canonical reference for the shortcut-* skill family (shortcut-create-ticket, shortcut-pickup-ticket, shortcut-done-audit, shortcut-priorities, shortcut-update-ticket, work-recap). Fix drift here, not per-skill.

## Token extraction

```bash
TOKEN=$(grep -a SHORTCUT_API_TOKEN ~/.claude/.env | sed 's/^\xef\xbb\xbf//' | cut -d= -f2 | tr -d '\r\n')
```

Header: `Shortcut-Token: $TOKEN`. Never write the token to a file — always inline `TOKEN=$(...)` in the same command that uses it.

## Fixed identity

- Dev Shortcut UUID: `699c76fe-9076-4424-ba22-2bb3534f417e`
- Dev mention name: `josipmui`
- Dev git author: `JosipMuzicZirtue` (email `josip.muzic+zirtue@cinnamon.agency`)

## ENG - Core Workflow (id `500018252`) states

- `500018253` Backlog (unstarted)
- `500018254` To Do (unstarted)
- `500018255` In Progress (started)
- `500018256` PR Review (started)
- `500018257` Testing (started)
- `500018415` Blocked (started)
- `500018659` Ready for deploy (started)
- `500019399` On hold (started)
- `500018258` Complete (done)
- `500019415` Won't do (done)

## ZNG repos (sibling absolute paths)

- `C:/Users/tecno/Desktop/Projects/zng-app`
- `C:/Users/tecno/Desktop/Projects/zng-admin`
- `C:/Users/tecno/Desktop/Projects/zng-api`
- `C:/Users/tecno/Desktop/Projects/zng-biller`

Fetch (never pull/checkout) before reading, when a skill needs current remote state.

## Git cross-reference recipe

```bash
git log --all --oneline -E --grep="^${id}:"
```

If no prefix match, also try a broad `--grep "$id"` to catch bundled references, but confirm any hit is actually about the ticket before treating it as related work — a 5-digit number can coincidentally match unrelated text.

## Fetching a story with comments

```bash
curl -s "https://api.app.shortcut.com/api/v3/stories/<id>" -H "Shortcut-Token: $TOKEN"
```

Full story JSON includes `comments[]`, `description`, `workflow_state_id`, `blocked`/`blocker`, `story_links`, `branches`, `pull_requests`, `commits`. Read `comments[]` in full, chronological order: a comment can silently reverse, narrow, or add scope the description never mentions (see `shortcut-pickup-ticket`). For provenance-checking a claim attributed to Shortcut (e.g. a todo's "per PM decision" citation), the comment thread is often the only place that backing actually lives.

## Searching stories

```bash
curl -s -G "https://api.app.shortcut.com/api/v3/search/stories" -H "Shortcut-Token: $TOKEN" \
  --data-urlencode "query=owner:josipmui !is:archived !is:done" --data-urlencode "page_size=25"
```

Common query operators: `owner:<mention>`, `!is:archived`, `!is:done`, `completed:<date>..*`, `title:"<exact phrase>"`. Paginate via the response's `.next` field (a full relative URL, `null` when exhausted): don't assume `page_size` alone means one page. The search API rejects `workflow_state_ids` as a query/body key; filter to specific states client-side after fetching.

**Free-text `query` is fuzzy/relevance-ranked, even combined with `state:"X"`: it returns unrelated stories ranked in, not a real AND filter.** `title:"exact phrase"` scopes more precisely. Carried forward, not re-verified this session (from a single hand-rolled-script session, 2026-08-13/14): a colon inside the quoted phrase (`title:"AP:"`) gets dropped, and the search falls back to matching the bare token as a substring of unrelated words (e.g. "Web App" contains "AP"), so a punctuated `title:` phrase needs a local post-filter on the returned `name` field before trusting the result set.

## Mutating a story: state-only PUT

```bash
curl -s -X PUT "https://api.app.shortcut.com/api/v3/stories/<id>" \
  -H "Shortcut-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"workflow_state_id":<target_id>}'
```

**Never include `custom_fields` in this PUT unless intentionally updating a field — the key REPLACES the entire array, wiping every other pinned value.**

## Posting a comment

```bash
curl -s -X POST "https://api.app.shortcut.com/api/v3/stories/<id>/comments" \
  -H "Shortcut-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"text":"<comment text>"}'
```

Only post when the dev gives exact text or explicitly asks — never draft-and-post in the same step.
