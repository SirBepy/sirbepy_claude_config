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

Follow **Window: daily (last working day)** in `../_common.md` (yesterday, or Friday after a weekend/Monday; announce the window before running commands).

### 2. Refresh the repo (read-only)

Follow **Repo refresh: fetch, never pull** in `../_common.md`, single repo:

```
git -C C:/Users/tecno/Desktop/Projects/fibo fetch --quiet
```

### 3. Pull commits

One Bash call:

```
git -C C:/Users/tecno/Desktop/Projects/fibo log --branches --author="JosipMuzicFibo" --since="<YYYY-MM-DD>" --pretty=format:"%h|%ad|%s" --date=format:"%H:%M"
```

Then apply **Commit dedupe (single-repo `--branches` scans)** from `../_common.md` (`--branches` not `--all`, dedupe by subject keeping earliest timestamp, drop stash/`Merge branch 'develop'` noise).

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

Write the two temp files per the **Clipboard helper contract** in `../_common.md` (blurb only, both HTML + plain-text formats, paths, escaping, verbatim titles, omit-empty-sections).

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

Escaping, verbatim titles, omit-empty: see the contract in `../_common.md`.

### 9. Push to clipboard

Invoke the helper per the **Clipboard helper contract** in `../_common.md` (one PowerShell call; never `clip.exe`; on failure note it but don't fail the flow).

### 10. Report

Print the blurb as a markdown blockquote in chat — always, regardless of the `copy` flag. Then on a new line, the absolute path to the markdown file. If clipboard copy succeeded, append " (copied to clipboard)".

## What this variant never does

- Never commits or pushes anything.
- Never pulls the repo (fetch only).
- Never invents PRs or commits. If a section has no data, omit it.
- Never touches GitHub Issues — this repo doesn't assign them per-dev, so they're not a signal here.
- Never uses `clip.exe`. Always go through the PS helper for clipboard.
- Never writes inside the fibo repo (output lives in `~/daily-recaps/`).
