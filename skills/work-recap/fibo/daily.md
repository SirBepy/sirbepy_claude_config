# work-recap: fibo daily

> Daily standup blurb for the Fibo monorepo: bullet list of what got done (yesterday/last working day) and what's planned today. Git + GitHub PRs only — no ticket tracker (Fibo has no per-dev Shortcut/Linear workflow; GitHub Issues in this repo aren't assigned per-dev). File is markdown (bullets + PR links). Clipboard on `copy` flag is HTML so pasted PR titles stay real hyperlinks in Slack/Teams.

## Dev identity (hardcoded)

- Git author name: `JosipMuzicFibo`
- Git author email: `josip.muzic@fibo.hr`
- GitHub account: `JosipMuzicFibo`

## Repo to scan

Single monorepo (not siblings like other groups' variants):

- `C:/Users/tecno/Desktop/Projects/fibo`

## Required tools

- Bash (`git -C <path> ...`, `gh pr list`)
- Write (the recap file + temp HTML file for clipboard)
- PowerShell (for `copy` flag, via `set-clipboard-html.ps1` helper)

`gh` runs against `Fibo-Studio/fibo` — the global `PreToolUse` hook auto-switches the active `gh` account to `JosipMuzicFibo` for this repo. No manual account switch needed.

## Flow

### 1. Compute the window

- Read today's date from the environment system reminder (`currentDate`). Do NOT hardcode.
- Find **last working day**:
  - Monday: window start = Friday (today - 3 days).
  - Sunday: window start = Friday (today - 2 days).
  - Saturday: window start = Friday (today - 1 day).
  - Otherwise: window start = yesterday (today - 1 day).
- Format start as `YYYY-MM-DD`. End = `now`.
- Announce the window in one sentence before running commands so the dev can correct it.

### 2. Refresh the repo (read-only)

One Bash call:

```
git -C C:/Users/tecno/Desktop/Projects/fibo fetch --quiet
```

No pulls. If fetch fails, note it and continue.

### 3. Pull commits

One Bash call. Use `--branches`, **not** `--all` — `--all` pulls in `refs/stash`, which produces bogus `WIP on <branch>: ...` / `index on <branch>: ...` entries that are stash commits, not real work:

```
git -C C:/Users/tecno/Desktop/Projects/fibo log --branches --author="JosipMuzicFibo" --since="<YYYY-MM-DD>" --pretty=format:"%h|%ad|%s" --date=format:"%H:%M"
```

**Dedupe by subject.** Squash-merged PRs and un-deleted local feature branches both leave a commit whose subject is identical to one already seen (different hash, same message) — this repo's `git log --branches` will show the same logical piece of work twice. Collapse duplicate subjects, keeping the earliest timestamp. Drop any subject starting with `WIP on ` or `index on ` (stash leftovers) and any bare `Merge branch 'develop'` noise commits.

Keep the deduped list internally — used to group bullets, not printed raw.

### 4. Pull PR state

Two calls:

**(a) Merged in window** — primary signal for Done:

```
gh pr list --repo Fibo-Studio/fibo --author JosipMuzicFibo --state merged --search "merged:>=<YYYY-MM-DD>" --json number,title,mergedAt,url --limit 30
```

**(b) Currently open** — always-included In Progress:

```
gh pr list --repo Fibo-Studio/fibo --author JosipMuzicFibo --state open --json number,title,url,isDraft --limit 30
```

### 5. Classify items

| Signal | Bucket |
|---|---|
| PR merged in window | Done |
| PR open (draft or ready) | In Progress (always-included) |
| Commit in window whose subject doesn't map to any PR in (a)/(b) — i.e. still un-PR'd on a local/pushed branch | In Progress (unticketed, noun phrase) |

There's no backlog/"Next up" bucket here — Fibo has no per-dev ticket queue to pull from. Skip that section entirely (unlike the zirtue variant).

Skip any bucket that has no items.

### 6. Compose the bullets

Rules:

- **Each bullet names what was worked on, NOT what was done.** No verbs like "shipped", "fixed", "added". Exception: PR titles are already imperative (`FEAT: ...`, `FIX: ...`) — keep them verbatim, don't re-verb them further.
- **Bullet = linked PR title**, verbatim from the `title` field, link = the PR `url`. Do NOT paraphrase.
- **Un-PR'd commits:** collapse into a short noun phrase per theme (e.g. `docs-site dark theme + PWA icon fixes`), no link. Group multiple related commit subjects into one line rather than listing each commit.
- **Multiple commits under one PR collapse into that one PR bullet.**
- **Skip empty buckets entirely.** If a section has nothing, omit the heading too.
- **Keep it tight.** 3-6 bullets per section max; if more, cap at 6 and append "and misc".
- **Blank line between sections.**

### 7. Write the markdown file (archive)

Path: `C:/Users/tecno/daily-recaps/<today_YYYY-MM-DD>_fibo_daily.md`

Create the directory if missing: `mkdir -p`.

Content:

```markdown
# Fibo Daily Standup - <today>

_Generated <today> by /work-recap fibo daily_

Done:
- [<PR title>](https://github.com/Fibo-Studio/fibo/pull/XXX)

In Progress:
- [<PR title>](https://github.com/Fibo-Studio/fibo/pull/XXX)
- <unticketed theme, short noun phrase>
```

Omit any section that has no items.

### 8. Build the clipboard payload (always)

Blurb only — no title, no `_Generated_` line, no file metadata.

Write TWO temp files so both HTML and plain-text clipboard formats are set. Slack prefers HTML (renders PR titles as real hyperlinks); plain text is the fallback (bare URLs auto-linkify).

**HTML file:** `C:/tmp/work-recap-clipboard.html`

```html
<html><body>
<p>Done:</p>
<ul>
<li><a href="https://github.com/Fibo-Studio/fibo/pull/118">FEAT: consume generated backend2 OpenAPI types via typed v2 helpers</a></li>
</ul>
<p>In Progress:</p>
<ul>
<li><a href="https://github.com/Fibo-Studio/fibo/pull/120">FEAT: something in review</a></li>
<li>docs-site dark theme + PWA icon fixes</li>
</ul>
</body></html>
```

**Plain-text file:** `C:/tmp/work-recap-clipboard.txt`

```
Done:
- FEAT: consume generated backend2 OpenAPI types via typed v2 helpers https://github.com/Fibo-Studio/fibo/pull/118

In Progress:
- FEAT: something in review https://github.com/Fibo-Studio/fibo/pull/120
- docs-site dark theme + PWA icon fixes
```

Notes:
- HTML: escape `<`, `>`, `&` inside titles as `&lt;`, `&gt;`, `&amp;`. Plain text: leave as-is.
- Omit any section whose list is empty (no heading either).
- PR titles come verbatim from `gh pr list`'s `title` field. Do NOT paraphrase.

### 9. Push to clipboard

One PowerShell call:

```
powershell -NoProfile -ExecutionPolicy Bypass -File "C:/Users/tecno/.claude/skills/work-recap/set-clipboard-html.ps1" -HtmlPath "C:/tmp/work-recap-clipboard.html" -TextPath "C:/tmp/work-recap-clipboard.txt"
```

If it fails, note it in the reply but don't fail the whole flow. NEVER use `clip.exe` (only writes `CF_TEXT`, loses hyperlinks).

### 10. Report

Print the blurb as a markdown blockquote in chat — always, regardless of the `copy` flag. Then on a new line, the absolute path to the markdown file. If clipboard copy succeeded, append " (copied to clipboard)".

## What this variant never does

- Never commits or pushes anything.
- Never pulls the repo (fetch only).
- Never invents PRs or commits. If a section has no data, omit it.
- Never touches GitHub Issues — this repo doesn't assign them per-dev, so they're not a signal here.
- Never uses `clip.exe`. Always go through the PS helper for clipboard.
- Never writes inside the fibo repo (output lives in `~/daily-recaps/`).

## Caveman mode

Status updates in chat stay caveman if active. The recap file itself and the clipboard payload are written normal.
