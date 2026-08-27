<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=EASY, worth=8, reconfirm-count=1, content-hash=62bfce2f -->
<!-- duplicate-checked -->
# /linear's lookup-by-ID recipe omits comments and relations, the two fields the rule says to always fetch

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `skills/linear/queries.md`'s issue-lookup recipe fetch a ticket's full context in one query,
so nobody hand-writes the GraphQL for it again and nobody answers off a stale description.

## Context

There is a standing project rule, captured in revaire-mobile's auto-memory as
`feedback_read_ticket_relations_first`: *"a Linear description can be years stale while the live
decision sits in a comment or a relation; fetch comments+relations+priorityLabel in the same
query."* It exists because it was learned the hard way.

`skills/linear/queries.md` does not support it. Grepped the file on 2026-08-21:
`comment`, `relation`, `inverseRelations` return **zero hits**. The lookup-by-ID recipe selects
scalar fields only.

Consequence, observed 2026-08-21 on revaire-mobile: answering "is there anything related to
REV-4810" required hand-writing the full query three times in a row (once for the issue, once for
three sibling issues, once for seven more). Every genuinely load-bearing fact in that answer came
from a **comment** or an **inverseRelation**, not a description - including the branch name a
colleague had forgotten, which sat in a comment dated four days earlier. The shipped recipe would
have returned none of it.

Prior art, both already done and neither covering this:
`done/linear-skill-selects-numeric-priority.md` fixed the same recipe's `priority` ->
`priorityLabel` but added no new edges. `done/387-linear-skill-still-owns-write-plumbing-after-the-ticket-merge.md`
moved the write side to `/ticket`.

## Approach

In `skills/linear/queries.md`, replace the lookup-by-ID recipe with a full-context one selecting,
in a single query: `description`, `priorityLabel`, `state`, `assignee`, `creator`, `project`,
`labels`, `parent`, `children`, `attachments`, plus

```graphql
comments { nodes { createdAt user { name } body } }
relations { nodes { type relatedIssue { identifier title state { name } assignee { name } } } }
inverseRelations { nodes { type issue { identifier title state { name } assignee { name } } } }
```

`inverseRelations` is the one most likely to be dropped and the one that carries "blocked by", so
call it out in a line of prose rather than leaving it to be inferred from the shape.

Add a one-line note under the recipe: a description alone is not an answer - read the comments,
newest first, before reporting what a ticket says.

Keep the shallow scalar-only recipe too, renamed as a list/table variant - it is the right shape
for the assigned-tickets and issues-in-project recipes, which should stay cheap.

## Acceptance

- `grep -niE "comments|inverseRelations" skills/linear/queries.md` returns hits.
- Running the new recipe against `REV-4810` returns its three Justin comments and both
  `inverseRelations` (REV-4807, REV-4809 as blockers).
- The existing list-shaped recipes still select `priorityLabel`, not bare `priority` - do not
  regress `done/linear-skill-selects-numeric-priority.md`.

## Notes

The helper itself is fine; this is purely a missing recipe. `Invoke-Linear` handled every one of
the hand-written queries without a change.
