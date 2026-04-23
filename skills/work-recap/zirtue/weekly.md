# work-recap: zirtue weekly

> Weekly work recap + next-week plan. Pulls signal from git (3 repos) and Shortcut (tickets owned by `josipmui`). Window: **previous Monday 00:00 local -> now**. Output: single markdown file, no chat dump.

## Dev identity (hardcoded)

- Shortcut user ID: `699c76fe-9076-4424-ba22-2bb3534f417e`
- Shortcut mention: `josipmui`
- Git author name: `JosipMuzicZirtue`
- Git author email: `tecnomon99@gmail.com`

## Repos to scan

All three live as siblings of `zng-app`:

- `C:/Users/tecno/Desktop/Projects/zng-app`
- `C:/Users/tecno/Desktop/Projects/zng-admin`
- `C:/Users/tecno/Desktop/Projects/zng-api`

## Required tools

- Bash (`git log`, `git -C <path>`)
- `mcp__shortcut__stories-search`
- `mcp__shortcut__stories-get-by-id` (only if a ticket summary needs enrichment)
- Write (the recap file)

If any Shortcut MCP call is denied, stop and tell the dev to loosen `.claude/settings.local.json`.

## Flow

### 1. Compute the window

- Read today's date from the environment system reminder (`currentDate`). Do NOT hardcode.
- Find **previous-week Monday** relative to today (the Monday of LAST calendar week, not the current week):
  - If today IS Monday, window start = Monday 7 days ago.
  - Else find this week's Monday, then subtract 7 days. Example: today Tue 2026-04-21 -> this week's Mon = 2026-04-20 -> window start = **2026-04-13**.
  - Never pick a Monday less than 7 days in the past.
- Format start as `YYYY-MM-DD`. End = `now`.
- Announce the window in one sentence before running commands so the dev can correct it.

### 2. Refresh sibling repos (read-only)

For each of the 3 repos run, one per Bash call (never chain):

```
git -C <repo> fetch --quiet
```

Do NOT `pull` (read-only recap, and the dev may have dirty state). Just fetch so `--all` branches are current for the log.

If a fetch fails (network, auth), note it in the output and keep going.

### 3. Pull commits per repo

For each repo, one Bash call:

```
git -C <repo> log --all --author="JosipMuzicZirtue" --author="tecnomon99@gmail.com" --since="<YYYY-MM-DD>" --pretty=format:"%h|%ad|%s" --date=short
```

- `--all` catches feature branches that never merged to develop/main.
- Both `--author` flags are OR'd by git.
- If output empty for a repo, record "no commits" for that repo.

### 4. Pull Shortcut tickets

One call:

```
mcp__shortcut__stories-search with:
  owner: "josipmui"
  isArchived: false
  updated: "<window start YYYY-MM-DD>..*"
```

(The `updated` param takes a range; `*` means open-ended. Single date = exact match, not "since".)

Capture: id, name, workflow_state, epic, estimate, updated_at.

If the search returns >25, just keep the top 25 most recently updated.

### 5. Derive next-week candidates

Combine three sources:

1. **Open tickets from the search** - anything not in a Done state. Rank:
   - `In Progress` first
   - then `In Review`
   - then `To Do` / `Ready`
   - ignore anything `Completed` / `Archived`
2. **Unfinished-from-last-week** - tickets that were updated but still aren't Done.
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

_Plain spoken sentences the dev can read aloud. No ticket numbers, no commit hashes, no Shortcut/epic/repo jargon. Talk about features and outcomes, not IDs. 4-8 sentences total: what got done last week, then what's up next week. First person ("I..."). Conversational, not a report._

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

| ID | Title | State | Epic | Estimate |
|----|-------|-------|------|----------|
| sc-XXXXX | ... | In Progress | ... | 3 |

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
- Repos scanned: zng-app, zng-admin, zng-api
- Shortcut filter: owner=josipmui, updated since <start>, not archived
- Commits by: JosipMuzicZirtue / tecnomon99@gmail.com
```

### 7. Report

One-line reply to the dev: absolute path to the file. Nothing else. No chat-inline summary.

## What this variant never does

- Never commits or pushes anything.
- Never pulls in sibling repos (fetch only).
- Never posts comments on Shortcut tickets.
- Never invents tickets or commits. If a section has no data, write "none" or omit it.
- Never dumps the full recap to chat. File path only.
- Never writes inside a project repo (output lives in `~/weekly-recaps/`).

## Caveman mode

If caveman mode is active during the run, status updates in chat stay caveman. The **recap file itself** is written normal (the dev reads it later out of context).
