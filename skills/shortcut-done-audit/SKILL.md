---
name: shortcut-done-audit
description: Triggers on /shortcut-done-audit only. Scans Joe's Shortcut tickets in Backlog/To Do/In Progress for ones with matching commits, then checks each for whether it's actually done, partially done, superseded, or misattributed. Always reports first; state changes only after Joe confirms per ticket.
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

Same as [[reference_shortcut_api_token]] / the release-backfill skill — never re-derive:

- Dev Shortcut UUID: `699c76fe-9076-4424-ba22-2bb3534f417e`
- Dev mention name: `josipmui`
- Dev git author: `JosipMuzicZirtue` (email `josip.muzic+zirtue@cinnamon.agency`)
- ENG - Core Workflow id: `500018252`, states:
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

Fan out in parallel — single message, multiple `Agent` calls, `model: 'sonnet'`, `subagent_type: 'general-purpose'`. Never use the Workflow tool for this unless Joe explicitly asks for orchestration (per global CLAUDE.md gate). When batching (volume gate triggered), give one subagent 2-3 tickets with clearly separated sections in the prompt and ask it to return one verdict block per ticket — don't blur evidence across tickets.

Each dispatch prompt must include, per ticket:

- The ticket ID, its current workflow state name, and every matching commit SHA + subject found in step 3 (or, for a soft match, the branch name and its tip SHA).
- **Explicit read-only instruction**: no comments posted, no workflow-state changes, no code edits, no commits, no `git checkout`/`pull` (repo is already fetched).
- Shortcut story-fetch command (same token pattern as step 2) — the story JSON includes `description`, `comments`, `pull_requests`, `branches`, `commits`, `labels`, `blocked`/`blocker`, `moved_at`. There is no separate history endpoint; infer state-lag from these fields plus git.
- Pre-computed mechanical facts so the subagent doesn't waste its own turns re-deriving them: whether each SHA is already an ancestor of `develop`/`main` (`git merge-base --is-ancestor <sha> develop`), and the branches it's contained in (`git branch -a --contains <sha>`) — hand these down as facts, don't make question 4 below re-run them per-agent.
- The five core questions, in this order, with "answer with evidence" (quote comment text, cite SHAs, cite file/line):
  1. **Was it returned?** Reviewer/QA pushback in comments, closed-unmerged or reopened PRs, rework-signaling labels.
  2. **Any new comments** — especially unanswered ones raising concerns.
  3. **Can you reproduce the described issue/behavior right now?** Case-by-case depth: read the current code and reason it through by default; only reach for `/run` or browser automation if code-reading is genuinely inconclusive (e.g. behavior depends on live API responses or timing) — don't default to booting the app for every ticket, it's slow and fragile across a batch.
  4. **Was it just done and never moved?** Use the pre-computed ancestor/branch facts above, plus whether the workflow state realistically lags the code.
  5. **MOST IMPORTANT — does the ticket's described scope match what was actually implemented?** Read the full description/AC, then `git show` every matching commit (or diff the branch against `develop` for a soft match), and call out any gap, partial coverage, or drift — not just "does it compile."
- If a sibling ticket shares a rename commit, an event name, or clearly overlapping scope (grep other tickets' titles/commits for the same feature area first), tell the subagent explicitly to check whether the sibling **supersedes** part of this ticket's AC — this was the single most valuable catch in the first run (54521 vs 54680).
- Ask for an overall verdict in a fixed vocabulary so the report step can group cleanly: `DONE`, `PARTIALLY DONE` (list gaps), `SUPERSEDED` (name the other ticket), `MISMATCH` (commits with the right ID prefix implement something else / real fix is unmerged), or `UNCLEAR`.

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

## Edge cases learned from the first run

- **Commit-prefix misattribution.** A ticket ID prefix on a commit message doesn't guarantee the commit implements that ticket — someone can typo/reuse an ID. Always cross-check the commit's actual diff against the ticket description, never trust the prefix alone. (Caught on 54263: two "54263:" commits on develop were unrelated work; the real fix sat unmerged on an abandoned branch.)
- **Sibling supersession.** Two FE tickets on the same feature area, worked back-to-back, can leave the older one's AC stale without either being "wrong" — the newer ticket intentionally replaced part of the older scope. Always check sibling tickets sharing a rename commit or the same feature folder before calling something a gap. (Caught on 54521 vs 54680.)
- **Stale-deploy false alarms.** A QA/PM comment reporting a bug "still happening" can predate the actual deploy of a fix that's already merged to `develop` — check commit timestamps vs comment timestamps before treating a comment as a real return. Still flag it as unanswered/unresolved even if likely stale; don't silently dismiss it.
- **Cross-codebase companion tickets.** Two tickets with near-identical titles/event names can be legitimately separate work in different repos (e.g. Framer/zirtue.com marketing site vs Flutter zng-app) rather than duplicates — check the description for explicit cross-references before flagging as a dupe.
- **Backlog with commits isn't automatically "board hygiene."** Don't assume a low-state ticket with matching commits must be understated — verify the commits are actually merged and actually match scope before recommending a forward move.

## What this skill never does

- Never mutates a ticket (state or comment) without Joe's explicit per-ticket go-ahead.
- Never posts a comment Joe didn't give exact text for or explicitly ask to post.
- Never includes `custom_fields` in a PUT unless intentionally updating a field (would wipe the rest of the array).
- Never treats a commit-message ID prefix as proof of scope match without reading the actual diff.
- Never edits code or commits in any repo — read-only investigation only.
