# Outbound ground check

> The shared gate every outbound ticket write passes before it happens. Extracted on 2026-08-18
> from what was then `skills/shortcut-create-ticket/ground-check.md`, so Linear stopped being
> ungated. That skill merged into `/ticket` later the same day and its copy is gone; this file is
> now the only definition, called from `skills/ticket/SKILL.md`.
>
> Enforced by `hooks/shortcut-create-guard.py` and `hooks/linear-create-guard.py`. Both consume
> the same marker, so this file is the single definition of when that marker may be written.

The incident this exists to prevent, 2026-08-14: a ticket was filed for work that was already
done, and the dev looked bad in front of his team. `CLAUDE.md`'s outbound rule states the
principle; this file is the executable half.

**The tracker is one of three places "already done" hides.** The other two are merged PRs and the
code itself, and no tracker search reaches either. That is why query 2 alone is not enough, on any
platform.

## Input: the stated claim

The draft must name what it asserts is missing or broken **as a literal string that will appear in
a `grep`** - a function, component, selector, or error text, not a paraphrase. `CreateLoan.tsx` +
`billerAddress` is a claim. "validation is missing on the loan screen" is not, and greps nothing.

If no literal string can be produced, say so in the report. An unstated claim means query 3 never
really ran, and a clean verdict would be false assurance.

## Query 1 - merged and open PRs (all platforms, unchanged)

Someone may have already shipped it, or be shipping it now.

```bash
gh pr list --state merged --search "<claim>" --limit 10 --json number,title,mergedAt,files
gh pr list --state open   --search "<claim>" --limit 10 --json number,title
```

## Query 2 - the tracker (platform-specific, the only part that differs)

Whatever the platform, the requirement is the same and is the thing a naive text search gets
wrong: **report the workflow state of every hit.** A finished ticket is not archived, so a Done
hit looks identical to an open one unless state is surfaced explicitly.

### Shortcut

Token extraction: `refs/shortcut-api.md`. Run 1-2 keyword variants, picking a distinctive noun,
never the title prefix.

```bash
curl -s -G "https://api.app.shortcut.com/api/v3/search/stories" -H "Shortcut-Token: $TOKEN" \
  --data-urlencode "query=<distinctive keyword>"
```

Surface `workflow_state_id` for every hit and name the state. State IDs are in
`refs/shortcut-api.md`. **Done and Testing are the states that matter.**

### Linear

Mechanics and the `Invoke-Linear` helper: `skills/linear/SKILL.md`. Linear returns state inline,
so no id lookup table is needed.

```graphql
query($q: String!) {
  searchIssues(term: $q, first: 10) {
    nodes { identifier title url state { name type } }
  }
}
```

**`state.type` is the field that matters, not `state.name`** - teams rename their columns freely,
but the type is a fixed enum. `completed` and `canceled` are Linear's equivalents of Done;
`started` is the equivalent of Testing for this check's purpose.

## Query 3 - the claim, at the tracked branch (all platforms, unchanged)

Not the dirty worktree, which may be stale or hold uncommitted work.

```bash
git fetch --quiet
git log --oneline -20 origin/<tracked-branch> -- <path>
git show origin/<tracked-branch>:<path> | grep -n "<claim>"
```

Resolve `<tracked-branch>` from the remote head (`git symbolic-ref refs/remotes/origin/HEAD`),
usually `develop` on the zng repos.

## Verdict

**HARD STOP** on any of these, and only these. They are high precision on purpose: a gate that
fires on maybes trains the dev to click through, which turns "stopped" back into "informed".

- A tracker hit already in a **done-equivalent state**: Shortcut `Done` or `Testing`, Linear
  `state.type` of `completed`, `canceled`, or `started`.
- A **merged PR** touching the file the claim names.
- For a bug: the asserted symptom is **absent** at the tracked branch (query 3 finds the guard,
  the fix, or the code already correct).

On a hard stop: **do not write the marker.** The write is blocked without it, which is the
mechanism, not a failure. Put the hit in front of the dev - id, state, URL, or PR number and merge
date - and stop. Filing anyway requires the dev to say so.

**SOFT** on a fuzzy keyword-only match with no state or file overlap: name it inline in the draft
and proceed. Soft signals never block.

**CLEAN** when nothing hits.

### Updates are a different question, and a narrower gate

For an UPDATE rather than a create, "somebody already did this" is not a reason to stop - the
ticket exists precisely because the work is live. Only **one** hard stop carries over: query 3
finding the claim absent at the tracked branch, which means the update is about to describe
something that is not true. Queries 1 and 2 are informational on an update path; report them,
never block on them.

Which fields count as claim-bearing per platform is defined once, in `hooks/_hooklib.py`'s
`CLAIM_FIELDS` mapping - not restated here. A state move or self-assign is never in that mapping
and stays ungated.

## Writing the marker, on a clean or soft verdict

```powershell
New-Item -ItemType File -Path "C:\Users\tecno\.claude\hooks\.outbound-marker-$([guid]::NewGuid().ToString('N'))" -Force | Out-Null
```

`New-Item`, never `Set-Content`/`Out-File`/`Add-Content`: `shell-content-write-guard.py` blocks
those three and its marker allowlist does not cover this name. The marker needs no content, so
nothing is lost.

The guards consume the oldest marker inside a **120 second** window, so write it immediately
before the write call, not earlier in the flow.

`.shortcut-marker-*` is the legacy name and is still accepted by the Shortcut guard so older
instructions keep working. New call sites write `.outbound-marker-*`.

## Report line, honest about its limits

A clean marker means these queries came back clean. It does not mean the work is undone. Say what
was checked and what cannot be:

```
Ground check: merged/open PRs (none), Linear "biller address" (ZNG-812 [state.type=started]),
CreateLoan.tsx @ origin/develop (claim present). Not checked: work resolved verbally, by config,
by another team, or by a hotfix leaves no trace in any of these.
```
