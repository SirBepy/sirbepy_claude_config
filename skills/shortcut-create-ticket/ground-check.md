# Ground check

> Called from `SKILL.md` step 2. Replaces the old tracker-only duplicate search, which could
> not see work that was already done. A ticket filed for already-finished work is the incident
> this exists to prevent (2026-08-14).

The tracker is one of three places "already done" hides. The other two are merged PRs and the
code itself, and a Shortcut search reaches neither.

## Input: the stated claim

Step 1 requires the draft to name what it asserts is missing or broken **as a literal string**
that will appear in a `grep` - a function, component, selector, or error text - not a
paraphrase. `CreateLoan.tsx` + `billerAddress` is a claim. "validation is missing on the loan
screen" is not, and greps nothing.

If no literal string can be produced, say so in the report. An unstated claim means query 3
never really ran, and a clean verdict would be false assurance.

## The three queries

Token extraction: `~/.claude/refs/shortcut-api.md`.

**1. Merged and open PRs.** Someone may have already shipped it, or be shipping it now.

```bash
gh pr list --state merged --search "<claim>" --limit 10 --json number,title,mergedAt,files
gh pr list --state open   --search "<claim>" --limit 10 --json number,title
```

**2. Shortcut, reporting workflow state.** The old check matched on text alone and filtered
`!is:archived`. A finished ticket is not archived, so a Done hit looked identical to an open
one. Surface `workflow_state_id` for every hit and name the state.

```bash
curl -s -G "https://api.app.shortcut.com/api/v3/search/stories" -H "Shortcut-Token: $TOKEN" \
  --data-urlencode "query=<distinctive keyword>"
```

Run 1-2 keyword variants. Pick a distinctive noun, never the title prefix. State IDs are in
`~/.claude/refs/shortcut-api.md`; Done and Testing are the ones that matter here.

**3. The claim, at the tracked branch.** Not the dirty worktree, which may be stale or hold
uncommitted work.

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

- A Shortcut hit whose workflow state is **Done** or **Testing**.
- A **merged PR** touching the file the claim names.
- For a bug: the asserted symptom is **absent** at the tracked branch (query 3 finds the guard,
  the fix, or the code already correct).

On a hard stop: **do not write the marker.** The create call is blocked without it, which is
the mechanism, not a failure. Put the hit in front of the dev - id, state, URL, or PR number
and merge date - and stop. Filing anyway requires the dev to say so.

**SOFT** on a fuzzy keyword-only match with no state or file overlap: name it inline in the
draft and proceed. Soft signals never block.

**CLEAN** when nothing hits.

## On a clean or soft verdict, write the marker

```powershell
New-Item -ItemType File -Path "C:\Users\tecno\.claude\hooks\.shortcut-marker-$([guid]::NewGuid().ToString('N'))" -Force | Out-Null
```

`New-Item`, never `Set-Content`/`Out-File`/`Add-Content`: `shell-content-write-guard.py`
blocks those three, and its marker allowlist covers only `.commit-marker` and `.pr-marker`.
The marker needs no content, so nothing is lost.

`shortcut-create-guard.py` consumes the oldest marker inside a 120s window, so write it
immediately before the create call, not earlier in the flow.

## Report line, honest about its limits

A clean marker means these queries came back clean. It does not mean the work is undone.
Say what was checked and what cannot be:

```
Ground check: merged/open PRs (none), Shortcut "biller address" (sc-8123 [In Progress]),
CreateLoan.tsx @ origin/develop (claim present). Not checked: work resolved verbally,
by config, by another team, or by a hotfix leaves no trace in any of these.
```
