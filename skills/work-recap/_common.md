# work-recap: shared rules

Single source of truth for the rules every variant used to copy-paste. Variant files point
at the named sections below; each variant keeps ONLY its own specifics inline (repo paths,
identities, data sources, output paths, payload structure). If you're running a variant,
read the sections it references and treat them as part of the variant's instructions.

## Window: weekly (previous-week Monday)

- Read today's date from the environment system reminder (`currentDate`). Do NOT hardcode.
- Find **previous-week Monday** relative to today (the Monday of LAST calendar week, not the current week):
  - If today IS Monday, window start = Monday 7 days ago.
  - Else find this week's Monday, then subtract 7 days. Example: today Tue 2026-04-21 -> this week's Mon = 2026-04-20 -> window start = **2026-04-13**.
  - Never pick a Monday less than 7 days in the past.
- Format start as `YYYY-MM-DD`. End = `now`.
- Announce the window in one sentence before running commands so the dev can correct it.

## Window: daily (last working day)

- Read today's date from the environment system reminder (`currentDate`). Do NOT hardcode.
- Find **last working day**:
  - Monday: window start = Friday (today - 3 days).
  - Sunday: window start = Friday (today - 2 days).
  - Saturday: window start = Friday (today - 1 day).
  - Otherwise: window start = yesterday (today - 1 day).
- Format start as `YYYY-MM-DD`. End = `now`.
- Announce the window in one sentence before running commands so the dev can correct it.

## Repo refresh: fetch, never pull

- One Bash call per repo:

  ```
  git -C <repo> fetch --quiet
  ```

- Do NOT `pull` (read-only recap, and the dev may have dirty state). Just fetch so remote branches are current for the log.
- If a fetch fails (network, auth), note it in the output and keep going.

## Commit dedupe (single-repo `--branches` scans)

Applies to variants that scan one repo with `git log --branches` (the fibo ones). The zirtue
variants keep their own multi-repo `--all` scan inline and do not use this section.

- Use `--branches`, **not** `--all` — `--all` pulls in `refs/stash`, which produces bogus `WIP on <branch>: ...` / `index on <branch>: ...` entries that are stash commits, not real work.
- **Dedupe by subject.** Squash-merged PRs and un-deleted local feature branches both leave a commit whose subject is identical to one already seen (different hash, same message). Collapse duplicate subjects, keeping the earliest date/timestamp.
- Drop any subject starting with `WIP on ` or `index on ` (stash leftovers) and bare `Merge branch 'develop'` noise commits.

## Clipboard helper contract (`set-clipboard-html.ps1`)

The helper lives at `C:/Users/tecno/.claude/skills/work-recap/set-clipboard-html.ps1`. It sets
BOTH clipboard formats via `System.Windows.Forms.DataObject`: HTML (`CF_HTML`, "HTML Format")
and plain text (`UnicodeText`). Slack/Teams read HTML first and paste real hyperlinks with the
title as label; if HTML is dropped, the plain-text fallback still gives bare URLs that auto-linkify.

**Inputs** — the variant writes TWO temp files before calling it:

- HTML fragment: `C:/tmp/work-recap-clipboard.html`
- Plain text: `C:/tmp/work-recap-clipboard.txt`

**Invocation** — one PowerShell call:

```
powershell -NoProfile -ExecutionPolicy Bypass -File "C:/Users/tecno/.claude/skills/work-recap/set-clipboard-html.ps1" -HtmlPath "C:/tmp/work-recap-clipboard.html" -TextPath "C:/tmp/work-recap-clipboard.txt"
```

**Rules shared by every clipboard payload:**

- NEVER use `clip.exe` — it only writes `CF_TEXT` and loses the HTML hyperlinks.
- If the PowerShell call fails, note it in the reply but don't fail the whole flow (the markdown file is still written).
- The payload is the blurb ONLY: no title, no `_Generated_` attribution, no file-metadata text.
- HTML: escape `<`, `>`, `&` inside titles as `&lt;`, `&gt;`, `&amp;`. Plain text: leave titles as-is.
- Titles come **verbatim** from the source (Shortcut `name` field / `gh pr list` `title` field). Do not rewrite, paraphrase, prefix, or trim.
- Omit any section whose list is empty (no heading either).
