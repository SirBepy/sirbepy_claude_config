# Outbound ground check

> The shared gate every outbound ticket write passes before it happens. Extracted on 2026-08-18
> from what was then `skills/shortcut-create-ticket/ground-check.md`, so Linear stopped being
> ungated. That skill merged into `/ticket` later the same day and its copy is gone; this file is
> now the only definition, called from `skills/ticket/SKILL.md`.
>
> Enforced by FOUR hooks, not two. All consume a fresh marker, so this file is the single
> definition of when one may be written:
>
> - `hooks/shortcut-create-guard.py` - blocks Shortcut story CREATION.
> - `hooks/linear-create-guard.py` - blocks Linear issue CREATION.
> - `hooks/linear-update-guard.py` - blocks CLAIM-BEARING Linear updates (title or description
>   rewrites, comments). A state move or self-assign asserts nothing and passes untouched.
> - `hooks/shortcut-mutation-guard.py` - blocks Shortcut mutations that rewrite ticket text, and
>   additionally requires every targeted story to be owned by `SHORTCUT_OWNER_UUID`.
>
> The two Shortcut guards also accept `.shortcut-marker*`, the legacy name kept for older
> instructions; the two Linear guards take `.outbound-marker*` only. New call sites write
> `.outbound-marker*`.

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

## Query 1 - merged and open PRs (all platforms)

Someone may have already shipped it, or be shipping it now. `gh pr list --search` answers an
unresolvable repo with an empty array, byte-identical to a genuine all-clear, while a plain `gh pr
list` fails loudly - so the repo must be proven to resolve before an empty result can be trusted.
Confirmed 2026-09-29 from a zng-api checkout on the `github-work` SSH alias: all three search
variants returned `[]`, but a bare `gh pr list --state merged --limit 5` failed with `Could not
resolve to a Repository with the name 'zirtue-corp/zng-api'`.

```bash
url=$(git remote get-url origin)
owner_repo=$(printf '%s' "$url" | sed -E 's#\.git$##' | sed -E 's#.*[:/]([^/]+/[^/]+)$#\1#')
gh repo view "$owner_repo" --json name >/dev/null || echo "UNVERIFIED: repo did not resolve"
gh pr list -R "$owner_repo" --state merged --search "<claim>" --limit 10 --json number,title,mergedAt,files
gh pr list -R "$owner_repo" --state open   --search "<claim>" --limit 10 --json number,title
```

Strip `.git` before extracting the last two path segments, in a separate `sed` pass: a one-pass
regex with a trailing optional `(\.git)?` gets swallowed by the greedy `[^/]+` before it and leaves
`.git` stuck on the repo name, which then fails to resolve (reproduced 2026-10-05 against this
repo's own `https://github.com/SirBepy/sirbepy_claude_config.git` origin).

If `gh repo view` fails, query 1's verdict is **UNVERIFIED**, not CLEAN: say so verbatim in the
report line below; queries 2 and 3 still decide the write. Root cause of a resolution failure is
usually the SSH host alias (`git@github-work:` is not `github.com`), but the recipe stays robust to
it either way rather than depending on the answer.

## Query 2 - the tracker (platform-specific, the only part that differs)

Whatever the platform, the requirement is the same and is the thing a naive text search gets
wrong: **report the workflow state of every hit.** A finished ticket is not archived, so a Done
hit looks identical to an open one unless state is surfaced explicitly.

### Shortcut

Token extraction and the search recipe: `refs/shortcut-api.md` ("Searching stories"). Run 1-2
keyword variants, picking a distinctive noun, never the title prefix, as the `query` value.

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

- A tracker hit already in a **done-equivalent state** (Shortcut `Done` or `Testing`, Linear
  `state.type` of `completed`, `canceled`, or `started`), or a **merged PR** touching the file the
  claim names - **only when query 3 also finds the claim absent** at the tracked branch. "A ticket
  reached Done" and "a PR touched this file" are not the same claim as "the behaviour exists",
  generically, not just for a BE/FE split: a done ticket can cover the other half of a BE/FE pair
  or an older era of the work - the same shape as a Done design-typed `UX:` ticket whose
  implementation was never filed - and a merged PR can be a refactor, rename, or extraction that
  touched the file without adding the behaviour. When query 3 finds the claim **present** instead,
  the hit demotes to REUSE CANDIDATE below: surface it to the dev (id, state, completion date, or
  PR number and merge date) and let him decide, rather than blocking the write.
  - 2026-09-24, sc-55728: BE ticket `Complete`, but the FE draft's endpoint call was still absent
    from the code and the limits were still hardcoded - the dev overrode by hand.
  - 2026-09-29, sc-56121: query 1 hit merged PR #833, a refactor that created the service with no
    resize call at `origin/develop` - the dev overrode by hand after seeing the false positive.
- For a bug: the asserted symptom is **absent** at the tracked branch (query 3 finds the guard,
  the fix, or the code already correct). Query 3 alone is the discriminator here; there is no
  tracker or PR hit to qualify.

On a hard stop: **do not write the marker.** The write is blocked without it, which is the
mechanism, not a failure. Put the hit in front of the dev - id, state, URL, or PR number and merge
date - and stop. Filing anyway requires the dev to say so.

**REUSE CANDIDATE** on a query-2 hit that is **open** and whose scope overlaps the draft's, not
merely the same feature area, **or** a done-state/merged-PR hit demoted by the query-3 qualifier
above. Do not write the marker and do not proceed to the creation questions. Put the hit to the dev
first: story id, title, type, state (or PR number and merge date), and a one-line reason the draft
is or is not the same unit of work. Creation proceeds only if the dev says it is genuinely
separate. Hit live 2026-09-01: sc-54902, an open `UX:` chore, read as "soft" because it was
design-typed and the draft was FE - the dev's answer was to reuse sc-54902 outright. A design-typed
hit is not automatically a different unit of work from its implementation.

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

Call the helper, never a hand-built `New-Item`/`Set-Content` call - todo 800: a raw write into
`hooks/` resolves as a hard deny in auto mode, with nobody to answer the resulting ask. The
script owns the join and guid generation and refuses to write a malformed marker, mirroring
`write-session-marker.ps1`'s shape (todo 365):

```powershell
& "C:\Users\tecno\.claude\hooks\write-outbound-marker.ps1"
```

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

When query 1's `gh repo view` fails to resolve, say **UNVERIFIED** verbatim rather than folding it
into CLEAN; it does not block the write, queries 2 and 3 still decide:

```
Ground check: merged/open PRs UNVERIFIED (gh could not resolve zirtue-corp/zng-api), Shortcut "..."
(none), <file> @ origin/develop (claim present).
```
