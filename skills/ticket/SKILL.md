---
name: ticket
description: Files, updates, or picks up a ticket, inferring the tracker from the repo's git remote (Shortcut for zirtue-corp, Linear for revaire). Use for "file a ticket", "log this as a bug", "update sc-12345", or picking up a story to work on.
argument-hint: "[create|update|pickup] <ticket id and/or free-form description>"
---

# /ticket

> One entrypoint for the three per-ticket operations. The tracker is looked up from the repo, never
> guessed and never asked about.

Replaced `shortcut-create-ticket`, `shortcut-update-ticket` and `shortcut-pickup-ticket` on
2026-08-18. Merged for **consistency of enforcement, not DRY** - the gate that blocks a create
against already-finished work only helps if every path reaches it.

## Step 0 - Resolve the tracker

`git remote get-url origin`, then match the owner. Same mechanism as `hooks/gh-account-switch.sh`,
which already maps this repo family for `gh` accounts.

| origin owner | Tracker | Quirks file |
|---|---|---|
| `zirtue-corp` | Shortcut (Zirtue) | `shortcut.md` |
| `revaire` | Linear (Revaire) | `linear.md` |
| anything else | **none - out of scope** | - |

**Out of scope means stop.** Fibo-Studio tracks tickets nowhere consistent (possibly Trello,
possibly Slack, possibly GitHub issues - unknown as of 2026-08-18), and personal repos have no
tracker at all. Name the remote, say no tracker is mapped for it, and stop. Never guess an org,
never fall back to the `.claude/todos/` backlog: that silently turns an outward-facing request into
a private note. Extend the table when a repo family actually gets a tracker.

Read the resolved quirks file in full before any API call. It carries the identity, endpoint,
pinned ids, and write mechanics that genuinely differ; everything below is shared.

## Step 1 - Resolve the verb

- An id plus field changes, or "move X to Y" -> **update**.
- A bare id, or "pick up X" / "what is X about" -> **pickup**.
- Anything else -> **create**.

Ambiguous between update and pickup on a bare id: pickup. It is the read-only one.

## Create

### 1. Ground the draft in current code first

Applies to FE "implement this design/flow" or "build Y screen" tickets against an existing app.
Skip for bugs, chores, and BE tickets.

Read the current implementation of the affected screen (an Explore subagent if it is a wide read)
and diff it against the new design. Never paraphrase a linked design ticket's spec text as if it
were that diff. Confirm whether the visual reference is a live-product screenshot or a Figma/Miro
mockup before picking a description shape: repro/actual/expected only fits a defect in a *running*
product. Default to one ticket per shared root cause, not one per symptom.

Past incident 2026-07-21: a ticket drafted by paraphrasing design-ticket spec text instead of
reading `zng-admin`'s actual biller-group screens landed wrong until the dev pointed at real code.

### 2. Front-load the questions

One `AskUserQuestion`, never open-ended, skipping anything the invocation already answered. What to
ask is platform-specific (Shortcut needs epic, priority and estimate; Linear needs team and
priority) - the quirks file lists them.

**State the claim.** Name the concrete file or behaviour the ticket asserts is missing or broken,
as a literal string that will appear in a `grep` - a function, component, selector, or error text,
never a paraphrase. That string is step 3's input, and without it step 3 cannot really run.

### 3. Ground check - MANDATORY, both platforms

Run `~/.claude/refs/outbound-ground-check.md` in full. It is platform-agnostic by design: queries 1
(merged/open PRs) and 3 (the claim at the tracked branch) are identical everywhere, and it carries
the per-tracker form of query 2 for both Shortcut and Linear.

- **Clean or soft:** write the marker exactly as that file specifies (`New-Item`, never
  `Set-Content`), immediately before the create call.
- **Hard stop:** do not write the marker. Report the hit and stop. `hooks/shortcut-create-guard.py`
  and `hooks/linear-create-guard.py` block the create without a fresh marker - that is the
  mechanism working, not a failure.

### 4. Description - smallest shape that fits

The dev consistently finds Claude-drafted tickets too long. When in doubt, write less.

- **Bug for a known engineer:** plain prose, 10 lines max, no headings, no QA criteria. One
  paragraph of what happens versus what is expected, then `Repro:` as 3-5 numbered steps.
- **Chore / small refactor:** 1-3 sentences. What, why, where. No headings.
- **Feature someone may pick up cold weeks later:** the full `# CONTEXT` / `# ACTION ITEMS` /
  `# ACCEPTANCE CRITERIA (QA)` template, with a Regression group. Only for multi-day features.

Relationships use the tracker's native link primitive, never a `# RELATED` prose block. Prefer
smaller scopes as well as smaller descriptions: two independently shippable chunks are two tickets.

### 5. Create, log, report

One API call per the quirks file. Capture the returned id and URL, append the log entry the quirks
file specifies, then tell the dev the id, the URL, and which defaults were applied.

## Update

### 1. Resolve the targets

Accept one or more ids plus the changes. For "all tickets matching X", search first and confirm the
resolved id list via `AskUserQuestion` before mutating anything. Never act on an inferred set.

### 2. Know which changes are claim-bearing

This is the distinction the guards enforce, so it decides whether step 3 runs:

- **Claim-bearing** - `name`, `description`, comments. These assert something about the world, so
  they get the ground check.
- **Not claim-bearing** - state moves, self-assign. Frictionless on purpose. Do not widen this
  without asking the dev.

### 3. Ground check, narrower than create's

Only for claim-bearing changes, and only **one** hard stop carries over: query 3 finding the claim
absent at the tracked branch, which means the update is about to describe something untrue. "This
already exists" is not a reason to stop an update - the ticket exists precisely because the work is
live. Queries 1 and 2 are informational here; report them, never block on them. Full rules are in
`refs/outbound-ground-check.md`'s own "Updates are a different question" section.

### 4. Write, one ticket at a time

Sequential, never parallel - it avoids rate-limit surprises and keeps the per-ticket report honest.
The write mechanics differ sharply per platform and both have a destructive failure mode; the
quirks file is not optional reading here. Report one line per ticket: id, title, fields changed,
before -> after for anything overwritten.

## Pickup

### 1. Fetch the full ticket - description AND every comment

**Non-negotiable, every pickup, no exceptions**, even when the ticket looks simple. Comments are
where scope actually gets revised: a QA note about a bug the description never mentions, a reviewer
rejecting the approach, a "let's do X instead". Caught live on sc-54229, where the description said
nothing about horizontal scrolling but a comment did, and that was the real ask.

Read every comment in chronological order. Never sample, never skim the last one only, never skip
because there are a lot. Download and Read any image attached to a comment - a screenshot is often
the clearest statement of the actual bug. Also read current state, blocked/blocker relationships,
and any linked branches, PRs or commits.

### 2. Cross-reference the code

In the current repo, plus any sibling repos the project's CLAUDE.md names as in-scope:

```bash
git log --all --oneline -E --grep="^<id>:"
```

No prefix match: retry with a broad `--grep "<id>"`, but confirm each hit is really about this
ticket. A 5-digit number matches unrelated text easily. Never treat an id in a commit message as
proof of scope match without reading the diff.

### 3. Summarize, then hand off

One tight paragraph: what the ticket asks for, its current state, whether work is already in
flight, any blocking relationship, and - called out explicitly, never buried - anything the
comments changed, added, or contradicted. If the comments added nothing, say that too, so it is
clear they were read.

Then offer to move it to In Progress via `AskUserQuestion`. Tracker state is shared, team-visible
state: never move it silently. If it is already further along than In Progress, do not offer to
move it backward - flag the mismatch and let the dev decide. Finish by asking what he wants next.

## What this skill never does

- Never files into a tracker it could not resolve from the remote.
- Never posts a comment without explicit approval.
- Never writes the ground-check marker on a hard stop.
- Never invents an id, UUID, or custom-field value. Unknown ones get fetched and pinned in the
  quirks file.
- Never generates branch names. The dev handles git.

## Out of scope, deliberately

- Cross-ticket sweeps: `/shortcut-priorities`, `/shortcut-done-audit`. They operate on a board, not
  a ticket, so they stay separate skills.
- Linear reads (search, list, lookup): `/linear` still owns those, along with the `Invoke-Linear`
  helper and the ownership gate that `linear.md` points at.
- Obsidian vault tickets: `/obsidian-pickup-ticket`. Explicitly out of the unification, per the dev
  on 2026-08-18.
