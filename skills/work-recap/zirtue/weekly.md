# work-recap: zirtue weekly

> Weekly work recap + next-week plan. Pulls signal from git (3 repos) and Shortcut (tickets owned by `josipmui`). Window: **previous Monday 00:00 local -> now**. Output: single markdown file, no chat dump.

## Dev identity (hardcoded)

- Shortcut user ID: `699c76fe-9076-4424-ba22-2bb3534f417e`
- Shortcut mention: `josipmui`
- Git author name: `JosipMuzicZirtue`
- Git author email: `josip.muzic+zirtue@cinnamon.agency`

## Repos to scan

All four live as siblings under the same parent folder:

- `C:/Users/tecno/Desktop/Projects/zng-app`
- `C:/Users/tecno/Desktop/Projects/zng-admin`
- `C:/Users/tecno/Desktop/Projects/zng-api`
- `C:/Users/tecno/Desktop/Projects/zng-biller`

## Required tools

- Bash (`git log`, `git -C <path>`, `curl` to api.app.shortcut.com)
- `mcp__shortcut__stories-search` and `mcp__shortcut__stories-get-by-id` **if available** (preferred when the MCP server is loaded in this session)
- Python (to parse `~/.claude/.env` and Shortcut JSON)
- AskUserQuestion (to pick backlog items for "Today")
- Write (the recap file)

### Shortcut access

The Shortcut MCP server is not always loaded. The user-level `~/.claude.json` typically lists only `figma` + `playwright`. Before using MCP, check via ToolSearch for `mcp__shortcut__*`. If absent, use the REST API directly:

```bash
python -c "import re; t=open(r'C:/Users/tecno/.claude/.env','r',encoding='utf-8-sig').read(); m=re.search(r'^SHORTCUT_API_TOKEN=(\S+)', t, re.M); print(m.group(1))" > C:/tmp/sc/tok
```

Notes:

- The `.env` file is UTF-8 **with BOM** and CRLF line endings. Bash `grep | cut` returns an empty string. Always read with Python `utf-8-sig`.
- `WebFetch` cannot send the `Shortcut-Token` header. Use `curl` via Bash.
- Token also unlocks `SHORTCUT_OWNER_UUID` (= `699c76fe-9076-4424-ba22-2bb3534f417e`).

If both MCP and the env token are missing, stop and tell the dev.

## Flow

### 1. Compute the window

Follow **Window: weekly (previous-week Monday)** in `../_common.md` (previous Monday of LAST week -> now; announce the window before running commands).

### 2. Refresh sibling repos (read-only)

For each repo, follow **Repo refresh: fetch, never pull** in `../_common.md` (one `git -C <repo> fetch --quiet` per Bash call; note failures and keep going).

### 3. Pull commits per repo

For each repo, one Bash call:

```
git -C <repo> log --all --author="josip.muzic+zirtue@cinnamon.agency" --since="<YYYY-MM-DD>" --pretty=format:"%h|%ad|%s" --date=short
```

- `--all` catches feature branches that never merged to develop/main.
- If output empty for a repo, record "no commits" for that repo.

### 4. Pull Shortcut tickets

**Two queries, both required:**

**(a) Commit-referenced tickets (primary signal for Done):**

First, extract all ticket IDs from the commits gathered in step 3. Commit subjects follow the pattern `NNNNN: ...` (bare number prefix) or `sc-NNNNN`. Collect the union across all repos.

For each extracted ID, fetch the ticket individually:

```bash
curl -s -H "Shortcut-Token: $(cat C:/tmp/sc/tok)" \
  "https://api.app.shortcut.com/api/v3/stories/<id>"
```

This is the authoritative Done list. Only tickets with a commit in the window belong in the "Shipped / merged" and "Done" sections of the recap and standup payload. Do NOT use `updated_at` to infer work was done — the dev may have bulk-updated ticket statuses on tickets completed weeks earlier.

**(b) Recently completed (secondary cross-check for Done):**

Search for tickets the dev owns that were **completed** (not just updated) in the window plus a 2-day buffer before the start, to catch tickets Joe finished just before the recap window. Use the `Searching stories` recipe in `~/.claude/refs/shortcut-api.md` (token from the extraction above): `query=owner:josipmui !is:archived completed:<buffer_start>..*`, `page_size=25`.

Where `<buffer_start>` = window start minus 2 days (e.g. if window starts 2026-05-12, use 2026-05-10).

Intersect this with the commit-referenced IDs from (a). A ticket belongs in Done only if it appears in **both** — completed recently AND has a commit in the repos. If a ticket is completed but has no commit in any repo this window, omit it from the recap (Joe likely marked it done without touching code in this window).

If a commit references a ticket that is NOT yet completed, include it in the recap under "Tickets touched" but NOT in the Done standup payload bucket — it's still in progress.

**(c) Currently-open:** all open tickets the dev owns (used to suggest "Today" candidates). Same recipe as (b): `query=owner:josipmui !is:archived !is:done`, `page_size=25`.

Paginate via `.next` per the ref, but stop early at ~50 results (deliberate bound, not full exhaustion), enough to surface today's candidates.

**State name resolution:** ticket JSON returns `workflow_state_id` (integer), not the state name. Fetch `/api/v3/workflows` once and build an id → (name, type) map. Cache for the rest of the run.

Capture per ticket: id, name, workflow_state (name + type), epic, estimate, completed_at.

If the secondary search returns >25, keep the top 25 most recently completed.

### 5. Derive next-week candidates

Combine three sources:

1. **Open tickets from the search** - anything not in a Done state. Rank:
   - `In Progress` first
   - then `In Review`
   - then `To Do` / `Ready`
   - ignore anything `Completed` / `Archived`
2. **Unfinished-from-last-week** - tickets referenced by a commit in the window but whose Shortcut state is still not Done.
3. **Inferred-from-commits** - look at commit subjects: if a ticket ID (`sc-XXXXX`) appears in a commit but the ticket isn't Done, flag it. If a feature branch has commits but no matching Shortcut ticket, call that out as "unticketed work, file one?".

Keep this list short: 3-6 items, priority-ordered. If there's an obvious next step implied by a commit ("Part 1 of ..."), surface it.

### 6. Write the file

Path: `C:/Users/tecno/weekly-recaps/<window_start_YYYY-MM-DD>_recap.md`

Create the directory if missing (one Bash call: `mkdir -p`).

File structure:

```markdown
# Weekly Recap - <window_start> to <today>

_Generated <today> by /work-recap zirtue weekly_

## TL;DR

<2-3 sentence prose summary: themes, biggest shipped thing, where focus landed.>

## Say it out loud (standup script)

_Plain spoken sentences the dev can read aloud. Audience is non-technical - no jargon, no framework names, no architecture terms. Talk about what users or the business can now do, not how it was built. Order: small items first, biggest thing last. 4-8 sentences total: what got done last week, then what's up next week. First person ("I..."). Conversational, not a report. Words to avoid: bootstrapped, scaffolded, NestJS, DTOs, controller, module, endpoint, repo, branch, deploy, refactor._

## Shipped / merged

### zng-app

- `<shortsha>` YYYY-MM-DD - <subject>
- ...

### zng-admin

- ...

### zng-api

- ...

(Omit a repo section entirely if it had zero commits.)

## Tickets touched (Shortcut)

| ID       | Title | State       | Epic | Estimate |
| -------- | ----- | ----------- | ---- | -------- |
| sc-XXXXX | ...   | In Progress | ...  | 3        |

Link each ID as `[sc-XXXXX](https://app.shortcut.com/zirtue/story/XXXXX)`.

## Themes / patterns

<1-3 bullets. What was the common thread? Biller flow? Auth? Bugs vs features? Only write this if a pattern is real, don't manufacture.>

## Next week - suggested focus

1. **sc-XXXXX - <title>** (<state>, <estimate>pt) - <one-line why: carry-over, blocker, next logical step>
2. ...

### Unticketed work spotted

- <repo>: <branch or commit cluster> - no matching Shortcut ticket. File one?

## Data sources

- Window: <start> -> <today>
- Repos scanned: zng-app, zng-admin, zng-api, zng-biller
- Shortcut filter: owner=josipmui, updated since <start>, not archived
- Commits by: JosipMuzicZirtue
```

### 6b. Verify "Doing" tickets actually shipped

Tickets in `Doing` state at fetch time may have actually been finished but the dev forgot to move them. Before pinning a `Doing` ticket to **Today**, scan its recent comments for a "done" signal from the dev (`josipmui`). If the most recent dev comment is silent and the ticket was last updated by someone else (designer, PM) >2 days ago, ask the dev: "did you finish this on Friday?" via AskUserQuestion.

If yes:

- Move the ticket from **Today** to **Done** in the payload.
- Offer to draft a "done" comment for the dev to paste on the ticket. Mention any teammates already tagged in the thread.
- Do **not** post the comment automatically — Shortcut mutations route through `mcp__shortcut__create-comment` and the `guard_mutation.py` hook requires explicit dev approval. Hand the draft to the dev for review.

### 7. Build the clipboard payload (only if `copy` flag passed)

No title, no attribution, no file metadata in the payload.

Two sections (skip either if empty):

- **Done:** tickets touched in the window whose Shortcut state maps to "merged / ready / accepted" (see bucketing table below). Verbatim ticket titles, linked.
- **Today:** what the dev plans to work on today. Always-pinned: anything currently in a true In-Progress state (`Doing` / `In Progress`). Plus zero-or-more backlog items picked by the dev via AskUserQuestion (see step 7b).

**No "Done + Tested" section in practice** — Zirtue's workflow uses `Ready for deploy` as the FE terminal state; QA acceptance happens after deploy and rarely reaches the FE dev within the same week. Keep the bucketing flexible: if a ticket really is in `Completed` / `Accepted`, split it out, otherwise fold everything into Done.

#### State bucketing (Zirtue workflows)

| Shortcut state                                                              | Bucket                                                          |
| --------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `Completed`, `Accepted`, `Tested`                                           | Done + Tested (rare)                                            |
| `Ready for deploy`, `Ready for Release`, `Merged`, `In Review`, `Blocked`\* | Done                                                            |
| `Doing`, `In Progress`                                                      | Today (always-pinned)                                           |
| `Backlog`, `To Do`, `Ready`                                                 | Today (only if dev picks via AskUserQuestion)                   |
| `Won't do`, `Duplicate`, `Archived`                                         | **Exclude** even if commits exist (work was reverted/abandoned) |

\* `Blocked` is ambiguous — if the ticket has merged commits in the window, treat as Done. If it was just touched but nothing shipped, omit.

Cross-check: if a commit subject references a ticket id (`sc-XXXXX`) but the ticket itself isn't in the search results (e.g. it was archived or moved), still include it with whatever state the individual `/stories/<id>` fetch returns.

#### Unticketed commits

**Default: omit.** Unticketed refactors, in-progress version bumps (`Version 49`, `1.0.0+8`), small cleanup commits do not belong in the standup payload.

Exception: a real released version. If a commit corresponds to a version that **actually shipped** (app store release, admin deploy hit prod), include as a noun phrase: `app v49 released`. The dev confirms shipping; do not infer from the commit alone. When in doubt, omit and tell the dev in chat.

Never include unticketed refactors, comments-only changes, or developer-only cleanup. Those belong in the recap file but not the clipboard payload.

#### Today section: picking backlog items

After determining the always-pinned In-Progress tickets, ask the dev which backlog items (if any) to add to Today. Use AskUserQuestion with `multiSelect: true`. Rank candidates:

1. **Recent + user-visible bugs / regressions** (titles containing `bug`, `Regression`, `broken`, `error`) updated in the last ~14 days.
2. **Recent feature tickets** updated in the last ~14 days, regardless of estimate.
3. **Stale tickets** updated >30 days ago — surface only if nothing fresher.

Surface 2–4 options in the question. Include `Doing`/`In Progress` tickets as always-pinned context in the question preamble, not as options. The dev may pick none ("just the in-progress one").

#### Payload structure

Write the two temp files per the **Clipboard helper contract** in `../_common.md` (paths, escaping, verbatim titles, omit-empty-sections). Weekly-specific: **insert a blank `<p>&nbsp;</p>` between sections in HTML, and TWO blank lines in plain text** — single blank line looks cramped in Slack/Teams.

**HTML file:** `C:/tmp/work-recap-clipboard.html`

```html
<html>
  <body>
    <p>Done:</p>
    <ul>
      <li>
        <a href="https://app.shortcut.com/zirtue/story/XXXXX"
          >Ticket title verbatim</a
        >
      </li>
    </ul>
    <p>&nbsp;</p>
    <p>Today:</p>
    <ul>
      <li>
        <a href="https://app.shortcut.com/zirtue/story/XXXXX"
          >Ticket title verbatim</a
        >
      </li>
    </ul>
  </body>
</html>
```

**Plain-text file:** `C:/tmp/work-recap-clipboard.txt`

```
Done:
- Ticket title verbatim https://app.shortcut.com/zirtue/story/XXXXX


Today:
- Ticket title verbatim https://app.shortcut.com/zirtue/story/XXXXX
```

Rules (escaping, verbatim titles, omit-empty: see the contract in `../_common.md`):

- If a title starts with `[FE]`, `[Regression]`, etc., keep it — verbatim means verbatim.
- The "no verbs" rule applies only to the rare unticketed noun-phrase bullet (see exception above), never to verbatim ticket titles.

### 8. Push to clipboard (only if `copy` flag passed)

Invoke the helper per the **Clipboard helper contract** in `../_common.md` (one PowerShell call; on failure note it but don't fail the flow).

### 9. Report

One-line reply to the dev: absolute path to the file. If `copy` ran successfully, add " (copied to clipboard)". Then paste the plain-text version of the clipboard payload (the `.txt` contents) into chat for review — the dev typically wants to sanity-check before pasting into Slack/Teams.

## What this variant never does

- Never commits or pushes anything.
- Never pulls in sibling repos (fetch only).
- Never posts comments on Shortcut tickets. Draft them and hand to the dev.
- Never invents tickets or commits. If a section has no data, write "none" or omit it.
- Never dumps the full recap markdown file to chat. The clipboard plain-text payload **is** pasted into chat for review (step 9).
- Never writes inside a project repo (output lives in `~/weekly-recaps/`).
- Never uses `clip.exe` (loses hyperlinks). Always go through the PS helper for clipboard.
- Never rewrites or paraphrases ticket titles. Verbatim from Shortcut `name` field.
- Never includes unticketed refactors, version bumps, or developer cleanup commits in the clipboard payload (the markdown recap file is fine to list them; the clipboard is for the standup, where it's noise).
