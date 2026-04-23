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

Split the combined commit + ticket signal into three buckets:

- **Yesterday's work (shipped / pushed / investigated):** tickets in done-ish states (`Completed`, `Merged`, `Ready for Release`), plus commits that landed on main-ish branches, plus any investigation-style tickets updated in the window but not assigned `In Progress` today.
- **Today's active work:** tickets in `In Progress` right now.
- **Carry-over candidate (only if today looks light):** top 1 from `Ready` / `To Do` / `In Review` the dev owns. Single pick, not a list.

### 6. Compose the bullets

Rules:

- **Each bullet names what was worked on, NOT what was done.** No verbs like "wrapped", "shipped", "pushed", "fixed". The reader (PM) only cares about the topic.
- **Bullet = linked ticket title.** Label is the Shortcut `name` field verbatim. Do NOT paraphrase, do NOT prepend a verb. The link URL is the Shortcut story URL.
- **Unticketed work:** a short noun phrase describing the area (not a full sentence). Example: `web login keystroke bug`. No link.
- **Multiple commits on one ticket collapse into one bullet.** Do not re-list the same ticket title.
- **Skip empty buckets entirely.** If a section has nothing, omit the section heading too.
- **Keep it tight.** 3-6 bullets per section max. If more, cap at 6, append one bullet "and misc".
- **Blank line between sections.** Yesterday, Today, and the "If I wrap early" line are each separated by a blank line for readability.

### 7. Write the markdown file (archive)

Path: `C:/Users/tecno/daily-recaps/<today_YYYY-MM-DD>_daily.md`

Create the directory if missing: `mkdir -p`.

Content (use markdown links `[title](url)` wrapping the ticket title, blank line between sections):

```markdown
# Daily Standup - <today>

_Generated <today> by /work-recap zirtue daily_

Yesterday:
- [<ticket title>](https://app.shortcut.com/zirtue/story/XXXXX)
- <unticketed area, short noun phrase>

Today:
- [<ticket title>](https://app.shortcut.com/zirtue/story/XXXXX)

If I wrap early: [<ticket title>](https://app.shortcut.com/zirtue/story/XXXXX)
```

(The "If I wrap early" line is included ONLY if today looks light per Step 5. Otherwise drop it entirely.)

If the `Today:` section would be empty (e.g., first thing in the morning with nothing assigned), keep the heading and write one bullet saying "plan TBD, will update after standup".

### 8. Build the clipboard payload (only if `copy` flag passed)

The clipboard payload is the BLURB ONLY. No `# Daily Standup` title. No `_Generated_` attribution. No file-metadata text.

Write TWO temp files so we can set BOTH HTML and plain-text clipboard formats. Slack prefers HTML (renders hyperlinks with the "sc-XXXXX" label), but if Slack drops HTML for any reason, the plain-text fallback still gives Slack bare URLs that auto-linkify.

**HTML file:** `C:/tmp/work-recap-clipboard.html`

Each bullet is just the linked ticket title (or unticketed noun phrase). No verbs. Section headings are `<p>` tags (which render with natural spacing in Slack paste).

```html
<html><body>
<p>Yesterday:</p>
<ul>
<li><a href="https://app.shortcut.com/zirtue/story/49222">Amplitude: Web App - Implement FE forgive-loan-tapped event</a></li>
<li><a href="https://app.shortcut.com/zirtue/story/49145">Amplitude: Web App - Implement FE loan-forgiven event</a></li>
<li><a href="https://app.shortcut.com/zirtue/story/53816">Biller flow: keep the flow for Registration Step 1 > Login redirection case</a></li>
<li>web login keystroke bug</li>
<li><a href="https://app.shortcut.com/zirtue/story/53794">[FE] Loan details: Incorrect copy for Deactivated status</a></li>
</ul>
<p>Today:</p>
<ul>
<li><a href="https://app.shortcut.com/zirtue/story/53794">[FE] Loan details: Incorrect copy for Deactivated status</a></li>
</ul>
<p>If I wrap early: <a href="https://app.shortcut.com/zirtue/story/53751">Biller deeplink flow: updating page breaks the deeplink flow</a></p>
</body></html>
```

**Plain-text file:** `C:/tmp/work-recap-clipboard.txt`

Same content, bare URLs after each title, blank lines between sections:

```
Yesterday:
- Amplitude: Web App - Implement FE forgive-loan-tapped event https://app.shortcut.com/zirtue/story/49222
- Amplitude: Web App - Implement FE loan-forgiven event https://app.shortcut.com/zirtue/story/49145
- Biller flow: keep the flow for Registration Step 1 > Login redirection case https://app.shortcut.com/zirtue/story/53816
- web login keystroke bug
- [FE] Loan details: Incorrect copy for Deactivated status https://app.shortcut.com/zirtue/story/53794

Today:
- [FE] Loan details: Incorrect copy for Deactivated status https://app.shortcut.com/zirtue/story/53794

If I wrap early: Biller deeplink flow: updating page breaks the deeplink flow https://app.shortcut.com/zirtue/story/53751
```

Notes:
- HTML: escape `<`, `>`, `&` inside ticket titles as `&lt;`, `&gt;`, `&amp;` (ticket titles CAN contain `<`, `>`, `&`, as seen in the example "Step 1 > Login"). Plain text: leave as-is.
- Omit the "If I wrap early" paragraph if today isn't light.
- Omit any section whose list is empty.
- Ticket titles come verbatim from the Shortcut search result's `name` field. Do NOT paraphrase them.
- No verbs anywhere. Each bullet is ONLY the topic.

### 9. Push to clipboard

Run once (one PowerShell call, no chaining):

```
powershell -NoProfile -ExecutionPolicy Bypass -File "C:/Users/tecno/.claude/skills/work-recap/set-clipboard-html.ps1" -HtmlPath "C:/tmp/work-recap-clipboard.html" -TextPath "C:/tmp/work-recap-clipboard.txt"
```

The helper uses `System.Windows.Forms.DataObject` with both HTML (`CF_HTML`) and UnicodeText formats. Slack reads HTML first and pastes hyperlinks with "sc-XXXXX" labels. If HTML is dropped, Slack falls back to the plain-text format, where bare URLs still auto-linkify.

If the PowerShell call fails, note it in the reply but don't fail the whole flow (the markdown file is still written). NEVER use `clip.exe` here: it only writes `CF_TEXT` and loses the HTML hyperlinks.

### 10. Report

One-line reply to the dev: absolute path to the file. If `copy` ran successfully, add " (copied to clipboard)". Nothing else. Do NOT paste the blurb into chat.

## What this variant never does

- Never commits or pushes anything.
- Never pulls in sibling repos (fetch only).
- Never posts comments on Shortcut tickets.
- Never invents tickets or commits. If a section has no data, omit it.
- Never dumps the full recap to chat. File path only.
- Never includes the file title or generator attribution in the clipboard payload.
- Never uses `clip.exe` (loses the hyperlinks, only CF_TEXT). Always go through the PS helper for clipboard.
- Never writes inside a project repo (output lives in `~/daily-recaps/`).

## Caveman mode

Status updates in chat stay caveman if active. The recap file itself and the clipboard payload are written normal.
