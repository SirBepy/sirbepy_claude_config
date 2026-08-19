# Linear quirks (Revaire)

> Loaded by `SKILL.md` step 0 when `origin` is a `revaire` repo. Only what differs from the shared
> flow lives here.

**Mechanics are not duplicated here.** `~/.claude/skills/linear/SKILL.md` owns the endpoint, the
auth header, the `Invoke-Linear` PowerShell helper, and the ownership gate. Read it before any call
and paste the helper into every tool call that uses it - PowerShell functions do not persist across
tool calls. `/linear` also keeps the read verbs (search, list, lookup) and its recipes in
`skills/linear/queries.md`.

Three things from that file matter enough to restate as pointers, because getting them wrong fails
silently:

- `Invoke-WebRequest`, never `Invoke-RestMethod` - the latter throws a no-parameterless-constructor
  error on PS 5.1 for some Linear payloads.
- Always check the `errors` array. Linear returns HTTP 200 with `data: null` on a bad query, so a
  broken query reads as "no results" without it. `Invoke-Linear` does this for you.
- Pass user input through `-Variables`, never string-interpolated into the query.

## The ownership gate is the hard part

`skills/linear/SKILL.md`'s "Write rules" section is the authority and must be re-read before any
mutation. The short version, because it decides what the update verb may do:

- **Always allowed:** create an issue (assigning it to anyone is fine), self-assign an issue whose
  `assignee` is currently null, any read.
- **Only on issues the dev CREATED** (`creator.id` matches his): title, description, labels,
  priority, estimate, project, delete.
- **On issues he did NOT create:** moving `stateId` while he is the assignee, and self-claiming an
  unassigned one. Nothing else - no typo fix, no appended note, no reformatting.

Before any `issueUpdate`, fetch `creator { id }` and `assignee { id }` and prove the edit is
allowed. If it is not, stop and tell the dev what you would have changed. Comments are additive and
fine anywhere - use one instead of editing someone else's description.

Note how this interacts with `SKILL.md`'s claim-bearing rule: title and description are both
claim-bearing AND creator-gated, so they need the ground check *and* the ownership proof. A state
move needs neither.

Teams: `REV` Revaire Product `2ae199d9-e3a7-49d1-8e1a-3268a97dc5de`, `REV2` Revaire Tasks
`0017fd8a-0a91-4123-914b-4c5f6ab6d7da`. Ids look like `REV-4833`, so REV is the default.

## Create

```powershell
# (paste the Invoke-Linear helper from skills/linear/SKILL.md first)
$q = 'mutation($input: IssueCreateInput!) { issueCreate(input: $input) { success issue { identifier url title } } }'
$vars = @{ input = @{
    teamId      = "2ae199d9-e3a7-49d1-8e1a-3268a97dc5de"   # REV
    title       = "..."
    description = "..."                                     # markdown
    assigneeId  = "..."                                     # optional
} }
(Invoke-Linear -Query $q -Variables $vars).issueCreate
```

**Questions to front-load:** title, team (REV unless told otherwise), priority, and assignee if it
is not the dev. There is no epic, iteration, estimate-in-points or custom-field ceremony here - that
is Shortcut's shape, not Linear's, so do not ask for them.

`hooks/linear-create-guard.py` blocks this mutation without a fresh ground-check marker, exactly as
the Shortcut guard does.

## Update

`issueUpdate` with the same `$input` shape. There is no destructive array-replacement hazard here -
Linear patches only the fields you send, so the GET-merge-PUT dance Shortcut needs does not apply.
The gate that does apply is ownership, above. `hooks/linear-update-guard.py` covers claim-bearing
updates (name, description, comments); state moves and self-assign pass through.

## Pickup

**Verified against the live API 2026-08-19** on REV-5345, which returned 2 comments and 1
attachment. One query gets everything the pickup flow needs, including the comment thread:

```powershell
# (paste the Invoke-Linear helper first)
$q = 'query($id:String!){ issue(id:$id){ identifier title description url
        state{ name type } assignee{ name } creator{ id name }
        comments{ nodes{ body createdAt user{ name } } }
        attachments{ nodes{ title url } } } }'
(Invoke-Linear -Query $q -Variables @{ id = "REV-4833" }).issue
```

- Team-prefixed ids like `REV-4833` work directly in `issue(id:)`; no UUID lookup needed.
- **Sort `comments.nodes` by `createdAt` yourself** before reading - do not assume the API returns
  them in order.
- `creator{ id }` comes back in the same call, so the ownership check for a later update costs no
  extra round trip. Fetch it here rather than re-querying.
- **`state.type`, not `state.name`**, is what a state check reads: teams rename columns freely, but
  the type is a fixed enum (`completed`, `canceled`, `started`, ...).

State move on go-ahead uses `issueUpdate` with `stateId`. Linear has no fixed global state ids like
Shortcut's - resolve the target state from the team's own workflow states first.

## Log

Same log as Shortcut, `~/.claude/skills/ticket/log.md`, same entry shape, with the URL being the
`https://linear.app/revaire/issue/REV-XXXX` form. Linear had no log before the merge; it gets one
now so the audit trail is not platform-dependent.
