# work-recap: zirtue daily

> Daily standup blurb: bullet list of what got done (yesterday/last working day) and what's planned today, plus a carry-over line if today looks light. File is markdown (bullets + `[sc-XXXXX](url)` links). Clipboard on `copy` flag is HTML so pasted "sc-XXXXX" stays a real hyperlink in Slack.

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
- Write (the recap file + the temp HTML file for clipboard)
- PowerShell (for `copy` flag, via `set-clipboard-html.ps1` helper)

If any Shortcut MCP call is denied, stop and tell the dev to loosen `.claude/settings.local.json`.

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

Keep the raw list internally. It's used to group bullets and correlate tickets, not printed.

### 4. Pull Shortcut tickets

One call:

```
mcp__shortcut__stories-search with:
  owner: "josipmui"
  isArchived: false
  updated: "<window start YYYY-MM-DD>..*"
```

Capture: id, name, workflow_state, epic, estimate, updated_at. Cap at 25 most recently updated if more.

### 5. Classify items

Split the combined commit + ticket signal into three buckets by Shortcut workflow state:

| Shortcut state | Bucket |
|---|---|
| `Completed`, `Accepted`, `Tested` | Done + Tested (rare) |
| `Ready for deploy`, `Ready for Release`, `Merged`, `In Review`, `Blocked`* | Done |
| `Doing`, `In Progress` | In Progress (always-included) |
| `Backlog`, `To Do`, `Ready` | Next up (single pick only, see below) |
| `Won't do`, `Duplicate`, `Archived` | **Exclude** |

\* `Blocked` - if the ticket has merged commits in the window, treat as Done. If nothing shipped, omit.

**Next up (optional):** If In Progress has ≤1 item, surface the single highest-priority candidate from `Ready` / `To Do` / `Backlog` owned by the dev. Prefer tickets with recent activity (updated last 7 days) or explicit `P1`/`P2` labels. One line only - not a list.

Skip any bucket that has no items.

### 6. Compose the bullets

Rules:

- **Each bullet names what was worked on, NOT what was done.** No verbs like "wrapped", "shipped", "pushed", "fixed". The reader (PM) only cares about the topic.
- **Bullet = linked ticket title.** Label is the Shortcut `name` field verbatim. Do NOT paraphrase, do NOT prepend a verb. The link URL is the Shortcut story URL.
- **Unticketed work:** a short noun phrase describing the area (not a full sentence). Example: `web login keystroke bug`. No link.
- **Multiple commits on one ticket collapse into one bullet.** Do not re-list the same ticket title.
- **Skip empty buckets entirely.** If a section has nothing, omit the section heading too.
- **Keep it tight.** 3-6 bullets per section max. If more, cap at 6, append one bullet "and misc".
- **Blank line between sections.**
- **Next up:** single line only. Format: `Next up: [<ticket title>](url)`. Omit if In Progress has ≥2 items.

### 7. Write the markdown file (archive)

Path: `C:/Users/tecno/daily-recaps/<today_YYYY-MM-DD>_daily.md`

Create the directory if missing: `mkdir -p`.

Content (use markdown links `[title](url)` wrapping the ticket title, blank line between sections):

```markdown
# Daily Standup - <today>

_Generated <today> by /work-recap zirtue daily_

Done + Tested:
- [<ticket title>](https://app.shortcut.com/zirtue/story/XXXXX)

Done:
- [<ticket title>](https://app.shortcut.com/zirtue/story/XXXXX)
- <unticketed area, short noun phrase>

In Progress:
- [<ticket title>](https://app.shortcut.com/zirtue/story/XXXXX)

Next up: [<ticket title>](https://app.shortcut.com/zirtue/story/XXXXX)
```

Omit any section that has no items. Omit "Next up" line if In Progress has ≥2 items.

### 8. Build the clipboard payload (always)

The clipboard payload is the BLURB ONLY. No `# Daily Standup` title. No `_Generated_` attribution. No file-metadata text.

Write TWO temp files so we can set BOTH HTML and plain-text clipboard formats. Slack prefers HTML (renders hyperlinks with the ticket title as label), but if Slack drops HTML for any reason, the plain-text fallback still gives Slack bare URLs that auto-linkify.

**HTML file:** `C:/tmp/work-recap-clipboard.html`

Sections are state-based: Done + Tested, Done, In Progress. Skip any section with no items. Section headings are `<p>` tags. Each bullet is the linked ticket title only, no verbs.

```html
<html><body>
<p>Done + Tested:</p>
<ul>
<li><a href="https://app.shortcut.com/zirtue/story/49222">Amplitude: Web App - Implement FE forgive-loan-tapped event</a></li>
<li><a href="https://app.shortcut.com/zirtue/story/49145">Amplitude: Web App - Implement FE loan-forgiven event</a></li>
</ul>
<p>Done:</p>
<ul>
<li><a href="https://app.shortcut.com/zirtue/story/53816">Biller flow: keep the flow for Registration Step 1 > Login redirection case</a></li>
<li>web login keystroke bug</li>
</ul>
<p>In Progress:</p>
<ul>
<li><a href="https://app.shortcut.com/zirtue/story/53794">[FE] Loan details: Incorrect copy for Deactivated status</a></li>
</ul>
</body></html>
```

**Plain-text file:** `C:/tmp/work-recap-clipboard.txt`

Same structure, bare URLs after each title, blank lines between sections:

```
Done + Tested:
- Amplitude: Web App - Implement FE forgive-loan-tapped event https://app.shortcut.com/zirtue/story/49222
- Amplitude: Web App - Implement FE loan-forgiven event https://app.shortcut.com/zirtue/story/49145

Done:
- Biller flow: keep the flow for Registration Step 1 > Login redirection case https://app.shortcut.com/zirtue/story/53816
- web login keystroke bug

In Progress:
- [FE] Loan details: Incorrect copy for Deactivated status https://app.shortcut.com/zirtue/story/53794
```

Notes:
- HTML: escape `<`, `>`, `&` inside ticket titles as `&lt;`, `&gt;`, `&amp;`. Plain text: leave as-is.
- Omit any section whose list is empty (no heading either).
- Ticket titles come verbatim from the Shortcut `name` field. Do NOT paraphrase them.
- No verbs anywhere. Each bullet is ONLY the topic.

### 9. Push to clipboard

Run once (one PowerShell call, no chaining):

```
powershell -NoProfile -ExecutionPolicy Bypass -File "C:/Users/tecno/.claude/skills/work-recap/set-clipboard-html.ps1" -HtmlPath "C:/tmp/work-recap-clipboard.html" -TextPath "C:/tmp/work-recap-clipboard.txt"
```

The helper uses `System.Windows.Forms.DataObject` with both HTML (`CF_HTML`) and UnicodeText formats. Slack reads HTML first and pastes hyperlinks with "sc-XXXXX" labels. If HTML is dropped, Slack falls back to the plain-text format, where bare URLs still auto-linkify.

If the PowerShell call fails, note it in the reply but don't fail the whole flow (the markdown file is still written). NEVER use `clip.exe` here: it only writes `CF_TEXT` and loses the HTML hyperlinks.

### 10. Report

Print the blurb as a markdown blockquote in chat — this is always done, regardless of the `copy` flag. Format: each section heading on its own `>` line, each bullet on its own `>` line, blank `>` line between sections. Then on a new line, print the absolute path to the markdown file. If clipboard copy ran successfully, append " (copied to clipboard)".

Example:
> Done:
> - [FE: Issue with Plaid (by Accrue)](https://app.shortcut.com/zirtue/story/54493)
>
> Next up: [FE: Framer & Amplitude integration for deeplinks tracking](https://app.shortcut.com/zirtue/story/54570)

`C:/Users/tecno/daily-recaps/2026-06-22_daily.md` (copied to clipboard)

## What this variant never does

- Never commits or pushes anything.
- Never pulls in sibling repos (fetch only).
- Never posts comments on Shortcut tickets.
- Never invents tickets or commits. If a section has no data, omit it.
- Never includes the file title or generator attribution in the clipboard payload or in-chat blockquote.
- Never uses `clip.exe` (loses the hyperlinks, only CF_TEXT). Always go through the PS helper for clipboard.
- Never writes inside a project repo (output lives in `~/daily-recaps/`).

## Caveman mode

Status updates in chat stay caveman if active. The recap file itself and the clipboard payload are written normal.
