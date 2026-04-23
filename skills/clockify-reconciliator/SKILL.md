---
name: clockify-reconciliator
description: Triggers on /clockify-reconciliator <project> only. Adds descriptions to description-less Clockify entries for a configured project, splitting large blocks into 1-3h chunks using git commits from configured repos.
argument-hint: <project-name> [lookback]
---

# /clockify-reconciliator

> Fill empty Clockify descriptions from git commits.

## Inputs

- `<project-name>` (required): matches `~/.claude/skills/clockify-reconciliator/projects/<project-name>.md`.
- `[lookback]` (optional): overrides default window. Accepted values:
  - `today` - today only (dev timezone)
  - `yesterday` - yesterday only (dev timezone)
  - `past-N-weeks` or `past-N-days` - rolling window ending now
  - `YYYY-MM-DD..YYYY-MM-DD` - explicit date range
  - Default if omitted: current work week (Mon to today, dev timezone).

## Prereqs

- `CLOCKIFY_API_KEY` env var set (or present in `~/.claude/.env`).
- Project config file exists. If missing, print the template below and abort.

## Project config template

Path: `~/.claude/skills/clockify-reconciliator/projects/<name>.md`

```
clockify_workspace_id: <id>
clockify_project_id: <id>
clockify_project_name: <display>
user_id: <clockify user id>
repos:
  - /abs/path/to/repo-1
  - /abs/path/to/repo-2
ticket_regex: (sc-\d+)   # optional, default (sc-\d+)|(#\d+)
```

## Steps

### 1. Load config

Read the named file. Abort with clear error listing missing required fields.

### 2. Resolve window

If `[lookback]` given, parse it. Else: Monday 00:00 of current week to now, in dev's timezone.

### 3. Fetch Clockify entries

Call `GET /workspaces/{ws}/user/{user}/time-entries?start=...&end=...&page-size=200`. Bucket:

- In-project (matches `clockify_project_id`)
- Other-project (for the warning)

### 4. Identify targets

Target = in-project entry with empty or whitespace-only description.

### 5. Read commits

For each repo in config: `git -C <repo> log --author="<user_id or name>" --since=... --until=... --pretty=format:...`. Capture sha, ISO timestamp, subject, body, branch (best-effort via `git branch --contains`).

### 6. Build proposals

For each target:

- Collect ALL dev commits for that calendar day across all configured repos (don't filter by the entry's time window).
- If duration > 3h, plan split into 1-3h chunks (prefer 1h or 2h). Respect original start + end total.
- Distribute the day's commits across chunks by rough chronology: earliest commits → earliest chunks. Assume the dev worked on things in the order committed, even if the commit timestamp falls outside the chunk (e.g. commit at 18:00 can describe the 15:00-17:00 chunk if it represents that chunk's work in the dev's workflow).
- Draft description from the chunk's assigned commit subjects. Max 80 chars. Drop filler to fit.
- If a matched commit subject hits `ticket_regex`, append ` (53794)` using just the captured number.
- If a day has zero commits at all across all repos, ask the dev what was done before proposing.

### 7. Warn on other-project entries

List description-less entries in OTHER projects in the same window. Dev handles those separately (could be a different config).

### 8. Present plan

Show a table: date, start-end, duration, proposed split, proposed description(s). Use AskUserQuestion:

- Apply all
- Apply some (pick which by index)
- Cancel

### 9. Apply

Approved rows only.

- Description-only: `PUT /workspaces/{ws}/time-entries/{id}` with updated description, preserving start/end/project/billable/tags.
- Split: shorten the original to the first chunk's end, then `POST /workspaces/{ws}/time-entries` for each remaining chunk with same project, same tags, contiguous times.

### 10. Report

- Entries written (count + per-day summary)
- "Needs manual" targets with time + reason
- Other-project warning list

## Rules

- Never touch an entry that already has a non-empty description.
- Never create entries in empty time ranges. Only operate on existing entries (splits allowed).
- Max 80 chars per description.
- Ticket suffix only if a matched commit carries one. One ticket per description, most relevant.
- No em dashes. Commas or hyphens.
