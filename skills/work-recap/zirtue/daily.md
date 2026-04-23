# work-recap: zirtue daily

> Daily recap: what got done yesterday (last working day), what's touched today so far, and a suggestion for tomorrow. Pulls signal from git (3 repos) and Shortcut (tickets owned by `josipmui`). Output: single markdown file, no chat dump.

## Dev identity (hardcoded)

- Shortcut user ID: `699c76fe-9076-4424-ba22-2bb3534f417e`
- Shortcut mention: `josipmui`
- Git author name: `JosipMuzicZirtue`
- Git author email: `tecnomon99@gmail.com`

## Repos to scan

Siblings of `zng-app`:

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
- Find **last working day**:
  - If today is Monday: window start = Friday (today - 3 days).
  - If today is Sunday: window start = Friday (today - 2 days).
  - If today is Saturday: window start = Friday (today - 1 day).
  - Otherwise: window start = yesterday (today - 1 day).
- Format start as `YYYY-MM-DD`. End = `now`.
- Announce the window in one sentence before running commands so the dev can correct it.

### 2. Refresh sibling repos (read-only)

For each of the 3 repos, one per Bash call:

```
git -C <repo> fetch --quiet
```

No pulls. If fetch fails, note it and continue.

### 3. Pull commits per repo

For each repo, one Bash call:

```
git -C <repo> log --all --author="JosipMuzicZirtue" --author="tecnomon99@gmail.com" --since="<YYYY-MM-DD>" --pretty=format:"%h|%ad|%s" --date=short
```

If empty, record "no commits" for that repo.

### 4. Pull Shortcut tickets

One call:

```
mcp__shortcut__stories-search with:
  owner: "josipmui"
  isArchived: false
  updated: "<window start YYYY-MM-DD>..*"
```

Capture: id, name, workflow_state, epic, estimate, updated_at. Cap at 25 most recently updated if more.

### 5. Derive tomorrow's candidate

Pick the single most likely "tomorrow focus":

1. Any ticket currently `In Progress` and not closed today -> top candidate.
2. Else: ticket tied to the most recent unmerged feature branch (commits today but no merge).
3. Else: top-ranked `In Review` or `Ready` ticket.
4. Else: if commits mention a `sc-XXXXX` still open, surface it.

Also flag up to 2 secondary candidates. Keep it small (1 primary + 0-2 backups).

### 6. Write the file

Path: `C:/Users/tecno/daily-recaps/<today_YYYY-MM-DD>_daily.md`

Create the directory if missing: `mkdir -p`.

File structure:

```markdown
# Daily Recap - <window_start> (<day>) -> <today>

_Generated <today> by /work-recap zirtue daily_

## Yesterday (or last working day)

<2-3 sentence prose: what got done, what shipped, any blockers hit.>

## Today so far

<1-2 sentence prose: what's being touched today, any active WIP branches.>

## Commits in window

### zng-app
- `<shortsha>` YYYY-MM-DD - <subject>

### zng-admin
- ...

### zng-api
- ...

(Omit a repo section if it had zero commits.)

## Tickets touched (Shortcut)

| ID | Title | State | Epic | Estimate |
|----|-------|-------|------|----------|
| sc-XXXXX | ... | In Progress | ... | 3 |

Link each ID as `[sc-XXXXX](https://app.shortcut.com/zirtue/story/XXXXX)`.

## Tomorrow - suggested focus

**Primary:** **sc-XXXXX - <title>** (<state>, <estimate>pt) - <one-line why>

**Backups:**
1. sc-XXXXX - <title> - <why>
2. sc-XXXXX - <title> - <why>

### Unticketed work spotted
- <repo>: <branch or commit cluster> - no matching Shortcut ticket. File one?

## Data sources

- Window: <start> -> <today>
- Repos scanned: zng-app, zng-admin, zng-api
- Shortcut filter: owner=josipmui, updated since <start>, not archived
- Commits by: JosipMuzicZirtue / tecnomon99@gmail.com
```

### 7. Report

One-line reply to the dev: absolute path to the file. Nothing else.

## What this variant never does

- Never commits or pushes anything.
- Never pulls in sibling repos (fetch only).
- Never posts comments on Shortcut tickets.
- Never invents tickets or commits. If a section has no data, write "none" or omit it.
- Never dumps the full recap to chat. File path only.
- Never writes inside a project repo (output lives in `~/daily-recaps/`).

## Caveman mode

Status updates in chat stay caveman if active. The recap file itself is written normal.
