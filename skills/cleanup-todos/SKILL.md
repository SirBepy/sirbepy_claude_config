---
name: cleanup-todos
description: Triggers on /cleanup-todos only. Dedupes todos and scores each for staleness, complexity and worth; archives dead ai-origin ones, never touches dev-origin unconfirmed.
---

# /cleanup-todos

> Dedupe, audit, and triage the todos backlog - everything confirm-gated before anything moves.

Backlog rules (location, format, claims, done/, PLAN.md) live in
`~/.claude/skills/close/ai-todos-format.md` - follow that contract for every file operation here.
Structural conventions (dry-run-confirm report style, EASY/HARD criteria) mirror
`~/.claude/skills/batch-todos/SKILL.md` - referenced below instead of restated.

This is a maintenance pass, not an execution skill: it never implements or executes a todo.

**Removal is gated by ORIGIN, not by a blanket confirm (dev standing instruction, 2026-08-12).**

- `**Origin:** dev` - never auto-archived, for any reason, at any score. It goes on the Step 6
  confirm list and waits. The dev's own intent is not Claude's to overrule.
- `**Origin:** ai`, or the field absent (unknown, treated as `ai` per the contract) - Step 7
  archives it WITHOUT asking when it is a proven-dead premise, a confirmed duplicate, or judged
  not worth doing. Say what was archived and why in the summary; do not ask first.

Archiving is never deletion - every removal goes to `done/` with a Notes line recording the reason,
so a wrong call is one `Move-Item` from undone.

Relocating a todo to a different repo's backlog (Step 4's `suggested_relocate`, Step 7) follows the
same origin gate as archiving - `ai`/absent-origin relocates without asking, `dev`-origin waits on
the Step 6 confirm list.

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

Sort every todo from Step 1 by ascending numeric id - this is the full pre-dedupe set. Split that
ranking into chunks of at most `DEEP_CHUNK_SIZE` (30) todos, and give the first `DEEP_MAX_CHUNKS`
(6) chunks a deep pass - 180 todos of real coverage. A dedupe-loser is chunked by its id like any
other todo, never added out-of-band.

The old rule deep-passed only the 40 lowest ids, which silently starved the NEWEST half of any
backlog past 40 - exactly the half most likely to still be wrong. Chunking replaces that.

**Deep pass:** dispatch one subagent per chunk (`model: 'sonnet'`, `effort: 'high'`), all chunks in
a single parallel dispatch, each carrying the full text of its own todos. Each returns one verdict
per todo, as prose (evidence, reasons) AND as one CSV row per todo appended at the end of its
report, header `file,complexity,worth,still_valid,relocate_dest` (the first four columns exactly
match `update-markers.ps1`'s columns, `file` is the exact backlog filename; `relocate_dest` is
Step 6/7's own field, ignored by `update-markers.ps1`). The main agent concatenates chunk CSVs (one
shared header) straight into Step 5's DataFile - it never retypes a verdict field by hand, the
transcription step that caused the 2026-08-12 corruption.

- `complexity`: EASY or HARD, same criteria table as `/batch-todos` step 3.
- `still_valid`: does the premise still hold? The check depth depends on the todo's `**Origin:**`:
  - `dev`-origin: a quick read of referenced files/paths, same spot-check as before - the premise
    is the dev's own intent, which cannot go stale the same way a Claude-noticed observation can.
  - `ai`-origin, or the field is absent (unknown, treated as `ai` per the contract): an actual
    re-verification against the current tree, not a spot-read - re-run the check the todo describes
    (grep the symbol, re-read the referenced lines, re-run the command it cites) and the verdict
    must cite the concrete evidence, `file:line` or the command run, rather than asserting validity.
- `suggested_drop`: true/false + one-line reason. Flag ONLY if the todo looks genuinely stale,
  superseded, or no-longer-relevant. Never flag on age or "not important" alone - that judgment
  belongs to the dev. Age is a report-level signal only (Step 6), never a triage verdict. An
  `ai`/unknown-origin todo whose re-verification comes back `still_valid: false` is ALWAYS
  `suggested_drop: true`, with the re-verification evidence as the reason - this is exactly the
  failure mode `**Origin:**` exists to catch. For an `ai`/absent-origin todo this flag is what
  Step 7 acts on directly; for a `dev`-origin one it only lands on the confirm list.
- `suggested_relocate`: blank, or `<dest-repo-root>|<reason>` when the todo's own subject names a
  different repo's files as its target, or names the global `~/.claude` tree while this backlog's
  own repo isn't `~/.claude` (the misfiled-global-todo case root `CLAUDE.md` documents). Cite the
  concrete path evidence. Only flag when the destination's `.claude/todos/` already exists on this
  machine - an unverifiable destination stays blank; note the suspicion in prose only, never guess
  a repo path.
- `worth`: an integer 1-10, plus a one-line `worth_reason`. This answers a question none of the
  other three do: **the premise can hold and the fix can be easy and it can still be a bad change
  to make.** Anchor to this rubric, never a vibe:
  - **9-10** - fixes a rule or script that has ALREADY misfired, with the incident cited.
  - **7-8** - closes a real gap that will recur; the change is bounded and its trigger is concrete.
  - **5-6** - genuine improvement, but speculative trigger or marginal payoff.
  - **3-4** - churn. Restates a rule that already exists elsewhere, or adds a rule with no
    enforcement path, or documents a preference as if it were a defect.
  - **1-2** - net negative. Contradicts an existing rule, over-fits a single incident, or adds
    surface area to a file that is already the bottleneck.

  Scoring the low end honestly is the whole point; a backlog where everything scores 7+ means the
  scorer was being polite, not that the backlog is good.

`worth` never feeds `suggested_drop` - they answer different questions and must be scored
independently. But on an `ai`/absent-origin todo a score of **4 or below is on its own sufficient
grounds for Step 7 to archive it**, separately from `suggested_drop`. On a `dev`-origin todo the
score is advisory only, forever.

Two carve-outs where a low score does NOT justify archiving, because the score is measuring the
wrong thing: a todo the dev explicitly parked ("do not build this unless I ask" scores low on
payoff while being a live instruction), and one whose action is the dev's own physical step
(revoking a credential, a console change). Surface those in the summary instead.

One subagent per chunk, never one dispatch per todo, and never a second tier of agents re-checking
the first.

**Shallow pass (overflow past `DEEP_CHUNK_SIZE * DEEP_MAX_CHUNKS`, if any):** main agent only, no
subagent, no content read. `complexity`, `still_valid` and `worth` are FORCED to the literal string
`"unknown (shallow pass)"`.
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
<!-- cleanup: last-checked <YYYY-MM-DD>, complexity=<value>, worth=<N>, reconfirm-count=<N>, content-hash=<H> -->
```

Skip this write entirely for any todo with a live, non-stale claim in `.claims/<id>.claim` (per
the contract's staleness definition: mtime + PID liveness) - note it in Step 6's table as
`claim-status: claimed - marker skipped`, so the report never rewrites a file another session is
actively working from.

**Deep-tier rows** (actually verified this run): `last-checked` bumps to today, and `worth` is
overwritten with this run's score - it is a re-judgement each time, never carried forward, since a
todo's worth changes as the repo around it changes. `content-hash` is
a short hash of the todo's Goal + Approach sections, recorded fresh each check. `reconfirm-count`
increments if `still_valid=true` AND the new `content-hash` matches the value stored in the todo's
previous marker; resets to 1 if the hash differs OR no previous marker exists (a todo's first-ever
check has nothing to compare against, so it's treated the same as a mismatch - a real, checkable
baseline instead of a best-effort read); holds steady (neither increments nor resets) if
`still_valid=false`.

**Shallow-tier rows** (never actually verified): `last-checked` is left UNCHANGED at its
pre-refresh snapshot value - nothing was checked, so nothing should look freshly checked. Only
`complexity=unknown (shallow pass)` is written; `worth`, `reconfirm-count` and `content-hash` are
left unchanged, so a real score from an earlier deep run survives an overflow run rather than being
stamped over with `unknown`. This keeps the staleness nag meaningful once a backlog exceeds the deep-tier cap:
shallow-tier todos keep aging in the nag like any other unattended todo, instead of resetting to
"fresh" on every run they overflow into the shallow tier.

**Diff gate - required before writing to the real backlog.** Copy `.claude/todos/` to a scratch
temp dir, run `update-markers.ps1` there with the real DataFile, then diff every touched file's
FULL content against the original - no filtering by the marker pattern, which is exactly what hid
the 2026-08-12 corruption (it excluded the one line class that broke). The only permitted
difference per file is one marker line added or replaced, above that file's first `# ` heading.
Any other change - a marker-shaped line altered below the heading, prose touched, a different file
changed - is a FAILURE: stop, report the offending file and diff, do not run against the real
backlog. Only once the gate passes does the run repeat against the real `.claude/todos/`.

## Step 6 - Report

Deliver as the turn's FINAL message - nothing may follow it in the same turn, since a same-turn
`AskUserQuestion` would swallow the preceding text in this harness, same reasoning as
`/batch-todos` step 4.

Contents, in order:

1. Folder-location audit hits (or "No stray locations found.").
2. Dedupe-pair count: "Dedupe pairs found: `<N>` (see confirm list below)." or "No duplicates
   found." if zero.
3. Staleness nag: "`<N>` todos not reconfirmed in `CLEANUP_STALE_DAYS` (14) days or more," computed
   from the PRE-refresh `last-checked` snapshot Step 5 recorded before overwriting it - never from
   the value Step 5 just wrote, which would always read as fresh.
4. A status table, fixed columns: `id | title | origin | worth | complexity | still_valid |
   reconfirm-count | triage-depth | claim-status`, sorted by `worth` ASCENDING so the weakest todos
   are the first thing read, not buried under 80 rows of fine ones. `origin` is the todo's
   `**Origin:**` value, or `unknown` if absent. `triage-depth` is `deep` or `shallow`.
   `claim-status` is blank or `claimed - marker skipped`.
4a. A **low-worth roundup**: every deep-tier todo scoring `worth <= 4`, as `id - title - score -
   worth_reason`. These are not drop suggestions and must not be presented as such; they are the
   list the dev scans to decide what is worth their tokens. State the count plainly, including
   when it is zero.
4b. An **archived** list: everything Step 7's Pass A already moved to `done/`, as `id - title -
   reason`. This is a record, not a proposal - it has already happened.
4c. A **relocated** list: everything Step 7's Pass A already moved to another repo's backlog, as
   `id -> new-id@dest-repo - reason`. Also a record, not a proposal.
5. A unified confirm list, `dev`-origin ONLY: every `origin: dedupe` loser appears here regardless of triage tier
   (Step 2 identifies duplicates across the whole backlog, independent of Step 4's deep-tier cap),
   plus every `origin: drop` suggestion (these are deep-tier only by construction, since shallow
   rows always have `suggested_drop` forced to `false` - not an extra exclusion rule, just a
   consequence of Step 4), plus every `dev`-origin `suggested_relocate` candidate (destination +
   reason). Each entry: id, title, one-line reason, origin(s).
6. A claims-check note: the check in Step 7 narrows but does not close a race with another session
   claiming a todo between this report and the dev's reply - worst case is a claimed todo gets
   archived, recoverable by moving it back out of `done/`.

Close by REPORTING what Step 7 already archived or relocated (ids + one-line reason each), then,
only if any `dev`-origin todo is pending: "Reply with ids to confirm the dev-origin items, or `keep
all`."
When nothing dev-origin is pending, close with no question at all - the run is finished.

## Step 7 - Apply confirmed items

This is the ONLY step in the skill that mutates backlog contents (file moves, PLAN.md prunes).

It runs in two passes, despite the step number:

- **Pass A, `ai`/absent-origin, BEFORE Step 6's report is written.** No reply needed, so the report
  describes finished work rather than a proposal. Everything below applies unchanged.
- **Pass B, `dev`-origin, after the dev's reply.** Only ids they named.

**Salvage before archiving a duplicate.** A dedupe loser often carries something the winner lacks -
sharper evidence, a second acceptance criterion, a sub-fix the winner marked optional. Read both,
fold anything unique into the winner, and say so in the loser's Notes line. Archiving a duplicate is
supposed to cost nothing; it costs something every time this is skipped.

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

**Relocate.** For a confirmed (or Pass-A, `ai`/absent-origin) `suggested_relocate` id:

1. **Content-duplicate check against the destination, first.** Apply `ai-todos-format.md`'s
   Content-duplicate guard to the DESTINATION backlog and its `done/`, keyed on this todo's
   subject - a relocation lands a file there like any other write and gets the same guard.
   - **Live match:** fold in there instead of writing a new file. Skip steps 2, 3 and 5.
   - **`done/` DONE match:** the relocation is stale. Skip steps 2, 3 and 5.
   - **`done/` DECLINED match, or a retired-rule hit per the guard's `git log` check:** skip steps
     2, 3 and 5, and carry the decline/retirement reason into step 4's Note and Step 6's report -
     this is the branch that stops a repeat filing on sight.
   - **No match:** continue to step 2.
2. Scan the destination's `.claude/todos/` and `done/` for the max numeric prefix, add 1, then
   re-check for a same-id collision per `ai-todos-format.md`'s creation race guard.
3. Write `<dest-repo>\.claude\todos\<new-id>-<same-slug>.md` via Edit/Write (never a shell
   redirect), same content plus a Notes line: "Relocated from `<old-id>` in `<source-repo>` via
   /cleanup-todos `<date>`: `<reason>`."
4. Run `complete-todo.ps1 -Id <old-id> -Note "<text>"` on the SOURCE repo - archives the source
   copy to its own `done/`, releases its claim, prunes its PLAN.md line. Never delete the source
   file directly. Note text: "Relocated to <new-id> in <dest-repo> via /cleanup-todos <date>." when
   step 3 wrote a file; otherwise step 1's matched outcome and reason (fold target id, or the
   done/decline text quoted).
5. Self-heal the destination's `.git/info/exclude` per this file's Git policy section if it's
   missing there - the destination may be a different repo with its own policy state. Only runs
   when step 3 actually wrote a file.

Bounded to destinations whose `.claude/todos/` already exists - relocate never invents a new
backlog folder.

If this project has opted into tracking `.claude/todos/` in git (per the contract's git policy -
check `git ls-files .claude/todos/`), run `/commit` once at the end of this run if EITHER Step 5
refreshed any marker OR Step 7 moved/pruned/relocated any file - covers a "keep all" reply where
only marker comments changed, not just the case where something got archived. This is a single
batched commit covering the whole run, not one per todo like `/batch-todos`. Most projects don't
track this folder by default, in which case there is nothing to commit.

## Unattended runs

Under `/autopilot` or an explicit no-input instruction, Step 6 still delivers its full report, but
Step 7 behaves exactly as in an attended run for `ai`/absent-origin todos - they are archived or
relocated on judgement, since no confirm was ever required for them. `dev`-origin candidates carry
into the closing summary as still-pending, for confirmation on a later run.

## Non-goals (v1)

- No coupling with `/batch-todos` - that skill is untouched; a redesign to consume cached
  complexity/dedupe results is a separate, later effort.
- No cron/scheduled-trigger wiring - manual invocation only. The staleness threshold is a
  report-time nag, not an enforced re-run mechanism.
- No auto-drop of a `dev`-origin todo, ever, under any condition. `ai`/absent-origin todos are
  archived on Claude's judgement without a confirm gate - see the origin rule at the top.
- No per-todo subagent dispatch for the deep tier - one batched call per CHUNK, capped at
  `DEEP_MAX_CHUNKS` chunks; overflow gets the shallow, content-blind pass instead of an unbounded
  fan-out or a second verifier tier.
- No plain deletion, ever. Every removal lands in `done/` with a Notes line stating the reason.

## Notes

- `CLEANUP_STALE_DAYS = 14` - the staleness-nag threshold. A constant, not a flag, for v1; tune
  here directly if it needs to change.
- `DEEP_CHUNK_SIZE = 30`, `DEEP_MAX_CHUNKS = 6` - 180 todos of deep coverage per run, chunked by
  ascending id over the full pre-dedupe set. Overflow gets the shallow pass (Step 4). Constants, not
  flags; tune here.
- `worth` is scored fresh every deep run and overwritten in the marker. Comparing a todo's old and
  new score across runs is not supported - the marker holds one value, the current one.
- Known residual, not fixed here: Step 4's deep-tier `still_valid` check overlaps with
  `/batch-todos` step 5's own validity check on the same files, with no cache-sharing between the
  two skills. Resolving it means touching `/batch-todos`, deferred to a separate later effort.
- Sibling divergence: `/cleanup-todos` archives duplicate-losers and confirmed drops to `done/`
  (contract-correct). `/batch-todos`'s own dedupe step currently deletes the loser outright - a
  pre-existing divergence from the parent contract that is not this skill's to fix.
- Source of truth: `.claude/todos/` only.
