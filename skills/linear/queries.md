# linear — query recipes

Ready-made GraphQL recipes for the `/linear` skill. Paste the `Invoke-Linear` helper from SKILL.md first, then run any of these.

## Primitives

### Look up ticket by ID (e.g. MOB-123) - full context

Linear accepts team-prefixed IDs like `MOB-123` directly in `issue(id:)`. A description can be years
stale while the live decision sits in a comment or a relation, so this recipe fetches everything in
one query: `description`, `priorityLabel`, `state`, `assignee`, `creator`, `project`, `labels`,
`parent`, `children`, `attachments`, `comments`, `relations` and `inverseRelations`.

**`inverseRelations` is the field most likely to be dropped from a hand-written query, and it's the
one that carries "blocked by"** - don't skip it.

```powershell
(Invoke-Linear -Query 'query($id:String!){ issue(id:$id){
    identifier title description url priorityLabel
    state{name} assignee{name} creator{name} project{name}
    labels{nodes{name}}
    parent{identifier title}
    children{nodes{identifier title state{name}}}
    attachments{nodes{title url}}
    comments{nodes{createdAt user{name} body}}
    relations{nodes{type relatedIssue{identifier title state{name} assignee{name}}}}
    inverseRelations{nodes{type issue{identifier title state{name} assignee{name}}}}
} }' -Variables @{ id = "MOB-123" }).issue
```

A description alone is not an answer - read `comments` newest-first before reporting what a ticket
says; the live decision is often in the most recent comment, not the description.

### Look up ticket by ID - shallow (list/table variant)

Same shape as the assigned-tickets and issues-in-project recipes below - scalar fields only, no
comments or relations. Use this for a cheap lookup when full context isn't needed.

```powershell
(Invoke-Linear -Query 'query($id:String!){ issue(id:$id){ identifier title description state{name} assignee{name} priorityLabel labels{nodes{name}} url } }' `
    -Variables @{ id = "MOB-123" }).issue
```

### Search tickets by keyword

Use **`searchIssues(term:)`**. Do NOT use `issueSearch(query:)` — it is **deprecated** and returns `{ errors: [{ message: "deprecated" }], data: null }` (so the helper above will throw a clear error rather than hand you an empty list).

```powershell
(Invoke-Linear -Query 'query($t:String!,$n:Int){ searchIssues(term:$t, first:$n){ pageInfo{ hasNextPage endCursor } nodes{ identifier title state{name} assignee{name} url } } }' `
    -Variables @{ t = "flight change"; n = 50 }).searchIssues.nodes
```

### List tickets assigned to the dev

```powershell
(Invoke-Linear -Query '{ issues(filter:{ assignee:{ isMe:{ eq:true } }, state:{ type:{ neq:"completed" } } }){ nodes{ identifier title state{name} priorityLabel dueDate url } } }').issues.nodes
```

Always select `priorityLabel` (String), never bare `priority` (Int, where 0 means No priority) - a low number is not a low P-number, it means unprioritised.

### List issues in a project or cycle (sprint)

Find the team's active cycle, then list its issues:

```powershell
(Invoke-Linear -Query '{ teams { nodes { id name activeCycle { id name startsAt endsAt } } } }').teams.nodes
```
```powershell
(Invoke-Linear -Query 'query($id:String!){ cycle(id:$id){ issues{ nodes{ identifier title state{name} assignee{name} } } } }' `
    -Variables @{ id = "CYCLE_ID" }).cycle.issues.nodes
```

### List projects

```powershell
(Invoke-Linear -Query '{ projects { nodes { id name state description url } } }').projects.nodes
```

### List issues in a project

```powershell
(Invoke-Linear -Query 'query($id:String!){ project(id:$id){ issues{ nodes{ identifier title state{name} assignee{name} url } } } }' `
    -Variables @{ id = "PROJECT_ID" }).project.issues.nodes
```

## Pagination (don't trust the first page)

Connection fields (`nodes`) return **only the first 50 results by default** - a "complete" list may be silently truncated. To get more, request a larger page with `first:` and follow the cursor:

```powershell
$all = @(); $after = $null
do {
    $page = (Invoke-Linear -Query 'query($t:String!,$a:String){ searchIssues(term:$t, first:50, after:$a){ pageInfo{ hasNextPage endCursor } nodes{ identifier title } } }' `
        -Variables @{ t = "flight change"; a = $after }).searchIssues
    $all += $page.nodes; $after = $page.pageInfo.endCursor
} while ($page.pageInfo.hasNextPage)
```

For a quick lookup the default 50 is fine - only loop when the user wants the full set or a count.
