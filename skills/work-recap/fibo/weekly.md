# work-recap: fibo weekly

> Weekly work recap + next-week plan for the Fibo monorepo. Pulls signal from git (single repo) and GitHub PRs (`Fibo-Studio/fibo`) — no ticket tracker (no per-dev Shortcut/Linear equivalent here; GitHub Issues in this repo aren't assigned per-dev). Window: **previous Monday 00:00 local -> now**. Output: single markdown file, no chat dump.

## Dev identity (hardcoded)

- Git author name: `JosipMuzicFibo`
- Git author email: `josip.muzic@fibo.hr`
- GitHub account: `JosipMuzicFibo`

## Repo to scan

Single monorepo (not siblings like other groups' variants):

- `C:/Users/tecno/Desktop/Projects/fibo`

## Required tools

- Bash (`git -C <path> ...`, `gh pr list`)
- Write (the recap file)

`gh` runs against `Fibo-Studio/fibo` — the global `PreToolUse` hook auto-switches the active `gh` account to `JosipMuzicFibo` for this repo. No manual account switch needed.

## Flow

### 1. Compute the window

Follow **Window: weekly (previous-week Monday)** in `../_common.md` (previous Monday of LAST week -> now; announce the window before running commands).

### 2. Refresh the repo (read-only)

Follow **Repo refresh: fetch, never pull** in `../_common.md`, single repo:

```
git -C C:/Users/tecno/Desktop/Projects/fibo fetch --quiet
```

### 3. Pull commits

One Bash call:

```
git -C C:/Users/tecno/Desktop/Projects/fibo log --branches --author="JosipMuzicFibo" --since="<YYYY-MM-DD>" --pretty=format:"%h|%ad|%s" --date=short
```

Then apply **Commit dedupe (single-repo `--branches` scans)** from `../_common.md` (`--branches` not `--all`, dedupe by subject keeping earliest date, drop stash/`Merge branch 'develop'` noise).

If output is empty, record "no commits this week".

### 4. Pull PR state

Three calls:

**(a) Merged in window** — authoritative Done list:

```
gh pr list --repo Fibo-Studio/fibo --author JosipMuzicFibo --state merged --search "merged:>=<YYYY-MM-DD>" --json number,title,mergedAt,url --limit 30
```

**(b) Currently open** — In Progress / next-week candidates:

```
gh pr list --repo Fibo-Studio/fibo --author JosipMuzicFibo --state open --json number,title,url,isDraft,createdAt --limit 30
```

**(c) Cross-check unticketed work:** commits from step 3 whose subject doesn't match any PR title from (a) or (b) — these are on a pushed-but-not-PR'd branch, or a local-only branch. Note the branch name if determinable (`git -C <repo> branch --contains <sha>`).

### 5. Derive next-week candidates

Combine:

1. **Open PRs** from (b) — ranked ready-for-review first, drafts second.
2. **Un-PR'd branches** from (c) — surface as "no PR yet, open one?" if the commits look finished (not a stash/WIP fragment).

Keep this list short: 3-6 items, priority-ordered.

### 6. Write the file

Path: `C:/Users/tecno/weekly-recaps/<window_start_YYYY-MM-DD>_fibo_recap.md`

Create the directory if missing (one Bash call: `mkdir -p`).

File structure:

```markdown
# Fibo Weekly Recap - <window_start> to <today>

_Generated <today> by /work-recap fibo weekly_

## TL;DR

<2-3 sentence prose summary: themes, biggest shipped thing, where focus landed.>

## Say it out loud (standup script)

_Plain spoken sentences the dev can read aloud. Audience is non-technical - no jargon, no framework names, no architecture terms. Talk about what the product/business can now do, not how it was built. Order: small items first, biggest thing last. 4-8 sentences total: what got done last week, then what's up next week. First person ("I..."). Conversational, not a report. Words to avoid: backend2, SQLModel, repository, service layer, migration, endpoint, branch, deploy, refactor._

## Shipped / merged

- `<PR #>` <mergedAt date> - <PR title, linked>
- ...

(If a PR merged with zero matching commits found in step 3 — e.g. someone else pushed the final commit — still list it; the PR is the authoritative Done signal, not the commit list.)

## In progress (open PRs)

| PR | Title | State | Opened |
| --- | --- | --- | --- |
| [#XXX](url) | ... | Draft / Ready for review | YYYY-MM-DD |

## Themes / patterns

<1-3 bullets. What was the common thread? Only write this if a pattern is real, don't manufacture.>

## Next week - suggested focus

1. **[#XXX](url) - <title>** (<state>) - <one-line why: carry-over, blocker, next logical step>
2. ...

### Unticketed work spotted

- <branch or commit cluster> - no matching PR. Open one?

## Data sources

- Window: <start> -> <today>
- Repo: Fibo-Studio/fibo (single monorepo, not siblings)
- Commits by: JosipMuzicFibo
- PRs by: JosipMuzicFibo (gh pr list, merged + open)
```

### 7. Report

One-line reply: absolute path to the file. No chat dump of the full recap — this variant never has a `copy` flag flow (no clipboard/standup payload; use the fibo `daily` variant for that).

## What this variant never does

- Never commits or pushes anything.
- Never pulls the repo (fetch only).
- Never invents PRs or commits. If a section has no data, write "none" or omit it.
- Never touches GitHub Issues — this repo doesn't assign them per-dev, so they're not a signal here.
- Never writes inside the fibo repo (output lives in `~/weekly-recaps/`).
- Never rewrites or paraphrases PR titles. Verbatim from `gh pr list`'s `title` field.
- The `copy` flag is a no-op for this variant (no clipboard payload defined) — if passed, note in the reply that it's ignored here.

## Caveman mode

If caveman mode is active during the run, status updates in chat stay caveman. The recap file itself is written normal (the dev reads it later out of context).
