---
name: linear
description: Triggers on /linear only. Query and create Linear tickets via the GraphQL API - search, list, look up, or file issues. Writes are tightly scoped - see the Write rules.
argument-hint: "<ticket-id or query>"
---

# /linear

> Read-only access to Linear tickets, projects, and sprints via the GraphQL API.

## Setup check

Before any API call, read `~/.claude/.env` and confirm `LINEAR_API_KEY` is present.

If missing, stop and tell the dev:

> Linear not set up. Add this to `~/.claude/.env`:
> ```
> LINEAR_API_KEY=lin_api_...
> ```
> Generate a personal API key at Linear → Settings → Account → Security & Access. Needs **write** scope for issue creation; the ownership gate below is what keeps writes safe, not the key scope.

## API basics

- Endpoint: `https://api.linear.app/graphql`
- Auth header: `Authorization: <key>` (NO "Bearer" prefix).
- POST, `Content-Type: application/json`, body is `{ "query": "...", "variables": {...} }`.
- The key is read from env every call, never hardcoded, never printed.

### The request helper — use this for every call

PowerShell functions do NOT persist between separate tool calls, so paste the whole helper into each call that uses it.

```powershell
function Invoke-Linear {
    param([Parameter(Mandatory)][string]$Query, [hashtable]$Variables)
    $key = ((Get-Content "C:\Users\tecno\.claude\.env" | Where-Object { $_ -match "^LINEAR_API_KEY=" }) -split "=", 2)[1].Trim()
    if (-not $key) { throw "LINEAR_API_KEY missing from ~/.claude/.env" }
    $payload = @{ query = $Query }
    if ($Variables) { $payload.variables = $Variables }
    $body = $payload | ConvertTo-Json -Depth 12 -Compress      # auto-escapes the query AND all variable values
    try {
        $resp = Invoke-WebRequest -Uri "https://api.linear.app/graphql" -Method POST `
            -Headers @{ Authorization = $key; "Content-Type" = "application/json" } -Body $body -UseBasicParsing
        $json = $resp.Content | ConvertFrom-Json
    } catch {
        # A bad/deprecated field returns HTTP 400; its GraphQL error body lives in ErrorDetails.
        if ($_.ErrorDetails.Message) { throw "Linear API error: $($_.ErrorDetails.Message)" } else { throw }
    }
    if ($json.errors) { throw "Linear GraphQL errors: $(($json.errors.message) -join '; ')" }  # 200-with-errors -> data is null
    return $json.data
}
```

**Why this shape (all verified against the live API on 2026-06-06):**
- **`Invoke-WebRequest`, not `Invoke-RestMethod`.** On Windows PowerShell 5.1, `Invoke-RestMethod` (and a bare `ConvertFrom-Json`) throw `No parameterless constructor defined for type of 'System.String'` on some Linear payloads. IWR + `.Content | ConvertFrom-Json` is reliable.
- **Always check `$json.errors`.** Linear signals a bad query with an `errors` array and `data: null` (HTTP 200 *or* 400). Without this check a broken query looks like "no results" - the single most common silent failure here.
- **Pass user input through `-Variables`, never string-interpolated into `$Query`.** `ConvertTo-Json` escapes it, so a search term containing `"` or `\` can't break the request or inject GraphQL.

### Sanity check (viewer)

```powershell
# (paste Invoke-Linear helper above first)
(Invoke-Linear -Query '{ viewer { id name email } }').viewer
```

## Query recipes

See `skills/linear/queries.md` for the ready-made recipes: lookup by ID, keyword search, tickets assigned to the dev, project/cycle listing, project listing, issues-in-project, and pagination.

## Output format

Always summarize cleanly - not raw JSON dumps:

```
MOB-123 — Flight Change Notification (In Progress)
Assigned: Josip Muzic | Priority: High
https://linear.app/revaire/issue/MOB-123
```

For lists, a compact table:
```
MOB-123  Flight Change Notification    In Progress   High
MOB-124  Push notification opt-in      Backlog       Medium
MOB-125  Booking confirmation screen   Done          Low
```

## Write rules - the ownership gate

Writes are allowed, but **ownership decides what you may touch**. The dev is
`Josip Muzic` (`bd12064d-f1d8-4ada-9e95-efda3df0ade6`). Someone else's ticket is
someone else's; a wrong edit is visible to the whole team and there is no undo.

**Always permitted:**

- **Create** a new issue (`issueCreate`). Assigning it to anyone is fine - filing
  a ticket for a colleague is normal, editing theirs is not.
- Any read.

**Permitted only on tickets the dev CREATED** (`creator.id` == the dev's id):

- Change `title`, `description`, labels, priority, estimate, project, or delete.

**The single exception on tickets the dev did NOT create:**

- **Moving `stateId` (status) - and nothing else - when the dev is the assignee**
  (`assignee.id` == the dev's id). Dragging your own card across the board is
  expected of you; rewriting the ticket is not.

**Never, on a ticket the dev did not create:**

- Touch `title` or `description`. No "small clarification", no typo fix, no
  reformatting, no appending a note. This is the rule that matters most.
- Reassign it, delete it, or change priority/labels/project.

**Before ANY `issueUpdate`,** fetch `creator { id }` and `assignee { id }` first
and prove the edit is allowed. If it isn't, stop and tell the dev what you would
have changed - never "just this once". Comments (`commentCreate`) are additive and
fine anywhere; use one instead of editing someone else's description.

### Create recipe

```powershell
# (paste Invoke-Linear helper above first)
$q = 'mutation($input: IssueCreateInput!) { issueCreate(input: $input) { success issue { identifier url title } } }'
$vars = @{ input = @{
    teamId      = "2ae199d9-e3a7-49d1-8e1a-3268a97dc5de"   # REV - Revaire Product
    title       = "..."
    description = "..."                                     # markdown
    assigneeId  = "..."                                     # optional
} }
(Invoke-Linear -Query $q -Variables $vars).issueCreate
```

Teams: `REV` Revaire Product `2ae199d9-e3a7-49d1-8e1a-3268a97dc5de` ·
`REV2` Revaire Tasks `0017fd8a-0a91-4123-914b-4c5f6ab6d7da`.
Ticket ids in this org look like `REV-4833`, so REV is the default unless told otherwise.

## Rules

- Reads are unrestricted. Writes follow the ownership gate above - re-read it before any mutation.
- Never print the API key. Never ask the dev for it - read from env only.
- Always go through `Invoke-Linear` so the `errors` array is checked - a silent empty result is usually a failed query, not zero matches.
- Pipe through ConvertFrom-Json / jq as needed.
