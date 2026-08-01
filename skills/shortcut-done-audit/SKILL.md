---
name: shortcut-done-audit
description: Scans the dev's Shortcut tickets in Backlog/To Do/In Progress for ones with matching commits, then checks each for whether it's actually done, partially done, superseded, or misattributed. Always reports first; state changes only after confirmation per ticket.
disable-model-invocation: true
argument-hint: "[states]"
---

# /shortcut-done-audit

> Find tickets assigned to Joe that say "not done" on the board but might already be done in the code — or the opposite, look done but aren't.

## Why this skill exists

- Joe ships code straight to `develop` in zng-app/zng-admin without always dragging the Shortcut card forward. Board state lags reality.
- The reverse also happens: a ticket has commits with the right ID prefix but they're unrelated work, or the real fix is stranded on an unmerged branch.
- Sibling tickets (e.g. two FE tickets on the same feature) can supersede each other's scope mid-flight — the older ticket's own acceptance criteria stop matching the app even though work "happened."
- This needs three independent lenses per ticket (returned? commented? scope match?) which is naturally a per-ticket subagent fan-out, not a single mechanical pass.

## Args

```
/shortcut-done-audit [states]
```

- `states` (optional) — comma-separated Shortcut state names to scan. Default: `Backlog,To Do,In Progress`.
- If Joe passes an unknown state name, ask via AskUserQuestion listing the actual state names from `ENG - Core Workflow` (workflow id `500018252`) rather than guessing.

## Required tools

- `Bash` — git log/show/branch in the three repos; curl against Shortcut REST API.
- `Agent` (`general-purpose`, model `sonnet`) — one per candidate ticket with commits. Run in parallel (single message, multiple Agent calls), not via the Workflow tool unless Joe explicitly asks for multi-agent orchestration.

**Shortcut API access:** token in `~/.claude/.env` as `SHORTCUT_API_TOKEN` (has a BOM, strip it), header `Shortcut-Token`. Never write the token to a file — always inline `TOKEN=$(...)` in the same command that uses it (writing it to disk gets blocked by the sandbox anyway).

## Fixed identity & constants

Dev UUID, mention name, git author, and workflow-state IDs: see `~/.claude/refs/shortcut-api.md`.

- Repos (sibling paths): `C:/Users/tecno/Desktop/Projects/zng-app`, `zng-admin`, `zng-api`. Fetch (never pull/checkout) before reading. zng-api is read-only for scope in this skill (Joe rarely authors there, but still check — a ticket could span BE too).
- State cache: `C:/Users/tecno/.claude/skills/shortcut-done-audit/state/audit_cache.json` — persists across runs (not `/tmp`, which can get cleared). Maps ticket ID → `{shas: [...], verdict, verdict_summary, audited_at}`.

## Flow

### 1. Refresh repos

```bash
git -C C:/Users/tecno/Desktop/Projects/zng-app fetch --quiet
git -C C:/Users/tecno/Desktop/Projects/zng-admin fetch --quiet
git -C C:/Users/tecno/Desktop/Projects/zng-api fetch --quiet
```

Stop and tell Joe if any fetch fails — don't reason against stale state.

### 2. Pull every ticket Joe owns, paginate, filter to target states

```bash
TOKEN=$(grep -a SHORTCUT_API_TOKEN ~/.claude/.env | sed 's/^\xef\xbb\xbf//' | cut -d= -f2 | tr -d '\r\n')
curl -s -G "https://api.app.shortcut.com/api/v3/search/stories" -H "Shortcut-Token: $TOKEN" \
  --data-urlencode "query=owner:josipmui" --data-urlencode "page_size=25" -o C:/tmp/sc_page_1.json
```

Follow `.next` across pages (it's a full relative URL, `null` when done) until exhausted — don't trust `page_size` alone to mean "one page." Filter the combined result client-side to the target `workflow_state_id`s (the search API rejects `workflow_state_ids` as a POST body key — filter after fetching, not in the query).

### 3. Match candidates to commits (primary + secondary signal)

For each candidate ticket ID, across all three repos:

```bash
git -C <repo> log --all --oneline -E --grep="^${id}:"
```

If no prefix match, also try a broad `--grep "$id"` per repo to catch bundled references (e.g. `52627: foo (52630)`), but treat broad matches with more suspicion — confirm in the investigation step that the match is actually about this ticket, not a coincidental 5-digit number.

**Secondary signal (don't rely on commit-message prefix alone — it misses squashed merges, differently-formatted subjects, and branch/PR-only work):** while fetching each candidate's story JSON anyway (needed for step 4/6), check its `branches` and `pull_requests` fields too. A non-empty `branches`/`pull_requests` with zero commit-grep hits is a **soft match** — still worth investigating, note in the dispatch prompt that detection came from branch/PR metadata, not a commit message, so the subagent should treat "does the code match scope" as more open-ended (can't `git show` a specific commit — needs to `git log` the branch or diff it against `develop` instead).

Tickets with **zero** signal from both commit-grep and branches/PRs: skip, no investigation needed, they're genuinely not started.

### 4. Check the dedupe cache before dispatching anything

Read `state/audit_cache.json` if it exists. For each matched candidate, compare its current SHA set (commit hits + any branch-tip SHA from the soft-match case) against the cached entry:

- **Unchanged since last audit** (same SHAs, cache entry exists): skip the subagent — reuse the cached verdict in the report, labeled `(cached from <audited_at>, unchanged)`. Don't re-burn tokens investigating a ticket nothing has moved on.
- **New or changed** (no cache entry, or SHAs differ): needs a fresh investigation in step 6.

If the cache file doesn't exist yet, treat every matched ticket as needing fresh investigation and create the file after step 6.

### 5. Dispatch-volume gate

Count how many tickets need a *fresh* investigation (post-dedupe). This is the actual cost driver — cap it here, not after the fact:

- **≤ 8 tickets:** dispatch one subagent per ticket (1:1), as below.
- **> 8 tickets:** stop and ask Joe via AskUserQuestion before firing anything: options along the lines of "investigate all (batched ~3 tickets/subagent to bound total agent count)", "investigate only the N most-recently-moved / highest-priority", or "cancel this run." Never silently fire 15+ parallel sonnet agents.

### 6. Dispatch investigation subagent(s)

Read `skills/shortcut-done-audit/investigation-prompt.md` now — it has the exact dispatch-prompt shape, the five core questions, and the edge cases learned from the first run. Fan out per that file's instructions: single message, multiple `Agent` calls, `model: 'sonnet'`, `subagent_type: 'general-purpose'`.

### 7. Synthesize the report

Group by verdict, most actionable first (`DONE` → `SUPERSEDED` → `PARTIALLY DONE` → `MISMATCH` → `UNCLEAR`). Include cached (unchanged) verdicts from step 4 in their group too, labeled as cached. For each ticket: one-paragraph summary, the concrete blocking detail if any (unanswered comment, missing per-button payload, unmerged branch, etc.), and a suggested next Shortcut state — but do not apply anything yet.

Report-only, no mutations, no comments — matches the pattern in `zirtue-release-backfill`.

### 8. Update the dedupe cache

After the report is delivered, write/merge the newly-investigated tickets into `state/audit_cache.json` (SHA set, verdict, one-line summary, `audited_at`). Cached (skipped) entries keep their existing cache row untouched. This is what makes the next run cheap.

### 9. Apply actions (only after Joe confirms, per ticket)

Once Joe responds with what he wants done (may be informal, e.g. "move X and Y to Testing, close Z as won't-do with comment '...'"), apply directly — no need for a formal multi-gate AskUserQuestion flow like the release-backfill skill, since findings are already ticket-scoped and Joe is confirming inline. Do ask a quick AskUserQuestion only when the target state is genuinely ambiguous (e.g. "close it" could mean `Complete` or `Won't do` — those have different semantic meaning and Joe should pick, don't default silently).

State-only change (no custom_fields touched — never include `custom_fields` in the PUT body unless Joe wants a field updated too, since including that key REPLACES the entire array):

```bash
curl -s -X PUT "https://api.app.shortcut.com/api/v3/stories/<id>" \
  -H "Shortcut-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"workflow_state_id":<target_id>}'
```

Comment:

```bash
curl -s -X POST "https://api.app.shortcut.com/api/v3/stories/<id>/comments" \
  -H "Shortcut-Token: $TOKEN" -H "Content-Type: application/json" \
  -d '{"text":"<comment text>"}'
```

Only post a comment when Joe gives the exact text or explicitly says to post one — never draft-and-post in the same step (per [[feedback_dont_post_drafts]]).

## What this skill never does

- Never mutates a ticket (state or comment) without Joe's explicit per-ticket go-ahead.
- Never posts a comment Joe didn't give exact text for or explicitly ask to post.
- Never includes `custom_fields` in a PUT unless intentionally updating a field (would wipe the rest of the array).
- Never treats a commit-message ID prefix as proof of scope match without reading the actual diff.
- Never edits code or commits in any repo — read-only investigation only.
