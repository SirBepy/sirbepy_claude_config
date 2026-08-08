---
name: cleanup-todos
description: Triggers on /cleanup-todos only. Dedupes and triages todos for staleness/complexity - never drops anything unconfirmed.
---

# /cleanup-todos

> Dedupe, audit, and triage the todos backlog - everything confirm-gated before anything moves.

Backlog rules (location, format, claims, done/, PLAN.md) live in
`~/.claude/skills/close/ai-todos-format.md` - follow that contract for every file operation here.
Structural conventions (dry-run-confirm report style, EASY/HARD criteria) mirror
`~/.claude/skills/batch-todos/SKILL.md` - referenced below instead of restated.

This is a maintenance pass, not an execution skill: it never implements or executes a todo. Every
action that removes a todo from the active backlog - a dedupe merge or a suggested drop - goes
through the SAME confirm gate in Step 7. Nothing moves before the dev replies.

## Step 1 - Read todos

Glob `.claude/todos/*.md`. Skip `PLAN.md` and any `done/` subfolder.

If empty: output "No todos found." and stop.

## Step 2 - Dedupe (read-only)

Read every file's title + Goal section, flag pairs describing the same underlying task
(near-identical titles, overlapping file/target references, same skill pointer for
`skill-improvement` type) - same criteria as `/batch-todos` step 2. For each duplicate pair,
identify which one has the more complete Context/Approach (or the lower id if tied) - that one is
kept. Tag the other as a proposed removal: `origin: dedupe`, with the kept id recorded.

Do NOT write or move anything in this step. No file writes, no PLAN.md pruning. The tagged list
carries forward into Steps 4 and 6 only.

## Step 3 - Folder-location audit

Check for exactly two known legacy shapes - nothing generic:

- A `todos/` directory sibling to `.claude/` at the repo root (not `.claude/todos/`).
- `.for_bepy/ai_todos/` (documented in CLAUDE.md as the pre-2026-07-15 legacy location).

If either exists with files in it, list them in the report as needing manual migration (reformat
to the `.claude/todos/` contract shape, then move). Do NOT auto-migrate - reformatting to contract
shape (adding required sections, assigning ids) is a judgment call for a human-reviewed pass, not
a blind move.

## Step 4 - Triage

Sort every todo from Step 1 by ascending numeric id - this is the full pre-dedupe set. The first
40 ids in that ranking get a deep pass; a dedupe-loser only gets the deep pass by ranking in the
first 40 like any other todo - it is never added out-of-band, and the 40-cap is never exceeded
regardless of how many dedupe-losers exist.

**Deep pass (first 40):** dispatch exactly ONE subagent (`model: 'sonnet'`) with the full text of
each of these todos in one prompt. It returns one verdict per todo:

- `complexity`: EASY or HARD, same criteria table as `/batch-todos` step 3.
- `still_valid`: does the premise still hold against a quick read of referenced files/paths? A
  spot-check, not a full re-implementation-level investigation.
- `suggested_drop`: true/false + one-line reason. Flag ONLY if the todo looks genuinely stale,
  superseded, or no-longer-relevant. Never flag on age or "not important" alone - that judgment
  belongs to the dev. Age is a report-level signal only (Step 6), never a triage verdict.

This must stay a single batched call for the deep tier, never one dispatch per todo.

**Shallow pass (remainder, if any):** main agent only, no subagent, no content read.
`complexity` and `still_valid` are FORCED to the literal string `"unknown (shallow pass)"`.
`suggested_drop` is FORCED `false` - a shallow-tier todo can never be independently flagged for
drop by this step's own verdict, though it can still appear in the Step 6 confirm list if Step 2
tagged it `origin: dedupe` (dedupe is backlog-wide and tier-agnostic, see Step 2). There is no
separate staleness computation here - `last-checked` is the sole staleness signal for every row,
deep or shallow, and Step 5 leaves it UNCHANGED for shallow-tier rows specifically, since nothing
about them was actually verified this run.

## Step 5 - Update markers

Before writing anything, for every todo still in the backlog after Step 1 (including any
pending/unconfirmed dedupe-losers - Step 2 is read-only, so nothing has actually been removed yet
at this point in the pipeline), record its EXISTING `last-checked` value from the current marker
comment, or `never` if it has none. This pre-refresh snapshot is what Step 6's staleness nag reads
- never the value this step is about to write.

Then refresh the marker comment near the top (alongside the existing `<!-- Claim before
executing: ... -->` line where present):

```
<!-- cleanup: last-checked <YYYY-MM-DD>, complexity=<value>, reconfirm-count=<N>, content-hash=<H> -->
```

Skip this write entirely for any todo with a live, non-stale claim in `.claims/<id>.claim` (per
the contract's staleness definition: mtime + PID liveness) - note it in Step 6's table as
`claim-status: claimed - marker skipped`, so the report never rewrites a file another session is
actively working from.

**Deep-tier rows** (actually verified this run): `last-checked` bumps to today. `content-hash` is
a short hash of the todo's Goal + Approach sections, recorded fresh each check. `reconfirm-count`
increments if `still_valid=true` AND the new `content-hash` matches the value stored in the todo's
previous marker; resets to 1 if the hash differs OR no previous marker exists (a todo's first-ever
check has nothing to compare against, so it's treated the same as a mismatch - a real, checkable
baseline instead of a best-effort read); holds steady (neither increments nor resets) if
`still_valid=false`.

**Shallow-tier rows** (never actually verified): `last-checked` is left UNCHANGED at its
pre-refresh snapshot value - nothing was checked, so nothing should look freshly checked. Only
`complexity=unknown (shallow pass)` is written; `reconfirm-count` and `content-hash` are left
unchanged. This keeps the staleness nag meaningful once a backlog exceeds the 40-todo triage cap:
shallow-tier todos keep aging in the nag like any other unattended todo, instead of resetting to
"fresh" on every run they overflow into the shallow tier.

## Step 6 - Report

Deliver as the turn's FINAL message, no tool call after it - a same-turn `AskUserQuestion` would
swallow the preceding text in this harness, same reasoning as `/batch-todos` step 4.

Contents, in order:

1. Folder-location audit hits (or "No stray locations found.").
2. Dedupe-pair count: "Dedupe pairs found: `<N>` (see confirm list below)." or "No duplicates
   found." if zero.
3. Staleness nag: "`<N>` todos not reconfirmed in `CLEANUP_STALE_DAYS` (14) days or more," computed
   from the PRE-refresh `last-checked` snapshot Step 5 recorded before overwriting it - never from
   the value Step 5 just wrote, which would always read as fresh.
4. A status table, fixed columns: `id | title | complexity | still_valid | reconfirm-count |
   triage-depth | claim-status`. `triage-depth` is `deep` or `shallow`. `claim-status` is blank or
   `claimed - marker skipped`.
5. A unified confirm list: every `origin: dedupe` loser appears here regardless of triage tier
   (Step 2 identifies duplicates across the whole backlog, independent of Step 4's 40-id cap),
   plus every `origin: drop` suggestion (these are deep-tier only by construction, since shallow
   rows always have `suggested_drop` forced to `false` - not an extra exclusion rule, just a
   consequence of Step 4). Each entry: id, title, one-line reason, origin(s).
6. A claims-check note: the check in Step 7 narrows but does not close a race with another session
   claiming a todo between this report and the dev's reply - worst case is a claimed todo gets
   archived, recoverable by moving it back out of `done/`.

Close with a plain-text prompt (not a tool call): "Reply with ids to confirm (covers both dedupe
merges and drops, e.g. `confirm 07 12`), or `keep all` to leave everything as-is."

## Step 7 - Apply confirmed items

This is the ONLY step in the skill that mutates backlog contents (file moves, PLAN.md prunes).

On the dev's reply, for each confirmed id: claims-check immediately before the move (right before
the write, not earlier - narrows the TOCTOU window from the whole report-to-reply gap down to a
single check-then-move). If the claims-check finds a live claim on a confirmed id at apply time:
skip only that id, do not abort the batch, continue processing the remaining confirmed ids. Append
one line per skipped id to the turn's closing message: "`<id>` - skipped, claimed by another
session mid-run; re-run /cleanup-todos to retry."

Otherwise: run `~/.claude/skills/close/complete-todo.ps1 -Id <id> -Note "<line per origin below>"`,
which records the Notes line, archives it to `done/`, prunes its PLAN.md line, and releases any
claim in one call (fall back to doing those four steps by hand if the helper is unavailable -
non-Windows, or missing):

- `origin: dedupe` only: "Duplicate of `<kept-id>` - merged during /cleanup-todos `<date>`.
  Confirmed by dev `<date>`."
- `origin: drop` only: "Dropped via /cleanup-todos `<date>`: `<reason>`. Confirmed by dev
  `<date>`."
- Both origins present (a todo that is a dedupe-loser AND was independently flagged
  `suggested_drop` by Step 4 for an unrelated reason): "Duplicate of `<kept-id>` AND independently
  flagged stale (`<reason>`) - merged/dropped during /cleanup-todos `<date>`. Confirmed by dev
  `<date>`."

Never plain-delete, per the contract.

If this project has opted into tracking `.claude/todos/` in git (per the contract's git policy -
check `git ls-files .claude/todos/`), run `/commit` once at the end of this run if EITHER Step 5
refreshed any marker OR Step 7 moved/pruned any file - covers a "keep all" reply where only marker
comments changed, not just the case where something got archived. This is a single batched commit
covering the whole run, not one per todo like `/batch-todos`. Most projects don't track this folder
by default, in which case there is nothing to commit.

## Unattended runs

Under `/autopilot` or an explicit no-input instruction, Step 6 still delivers its full report, but
Step 7 auto-resolves as `keep all`: no merges, no drops, nothing archived. Every dedupe pair and
`suggested_drop` candidate from Step 6's confirm list carries into the run's closing summary as
still-pending, for confirmation on a later run. This never overrides the no-auto-drop rule below.

## Non-goals (v1)

- No coupling with `/batch-todos` - that skill is untouched; a redesign to consume cached
  complexity/dedupe results is a separate, later effort.
- No cron/scheduled-trigger wiring - manual invocation only. The staleness threshold is a
  report-time nag, not an enforced re-run mechanism.
- No auto-drop, ever, under any condition - every removal from the backlog goes through the Step 7
  confirm gate, including dedupe merges.
- No per-todo subagent dispatch for the deep tier - one batched call per cleanup run, capped at 40
  todos; overflow gets the shallow, content-blind pass instead of a second subagent tier or chunked
  multi-dispatch.

## Notes

- `CLEANUP_STALE_DAYS = 14` - the staleness-nag threshold. A constant, not a flag, for v1; tune
  here directly if it needs to change.
- Deep-tier triage cap: 40 todos, selected by ascending id order over the full pre-dedupe set.
  Overflow gets the shallow pass (Step 4).
- Known residual, not fixed here: Step 4's deep-tier `still_valid` check overlaps with
  `/batch-todos` step 5's own validity check on the same files, with no cache-sharing between the
  two skills. Resolving it means touching `/batch-todos`, deferred to a separate later effort.
- Sibling divergence: `/cleanup-todos` archives duplicate-losers and confirmed drops to `done/`
  (contract-correct). `/batch-todos`'s own dedupe step currently deletes the loser outright - a
  pre-existing divergence from the parent contract that is not this skill's to fix.
- Source of truth: `.claude/todos/` only.
