---
name: batch-todos
description: Triggers on /batch-todos only. Dedupes todos, auto-executes EASY ones after a dry-run confirm, then surfaces the HARD queue.
---

# /batch-todos

> Dedupe AI todos, auto-batch the easy ones, then surface the hard ones for the dev to choose.

Backlog rules (location, format, claims, done/, PLAN.md) live in
`~/.claude/skills/close/ai-todos-format.md` - follow that contract for every file operation here.

## Step 1 - Read todos

Glob `.claude/todos/*.md`. Skip `PLAN.md` and any `done/` subfolder.

If empty: output "No todos found." and stop.

## Step 2 - Dedupe

Read every file's title + Goal section. Flag pairs that describe the same underlying task or the same skill-improvement observation (near-identical titles, overlapping file/target references, same skill pointer for `skill-improvement` type).

For each duplicate pair: keep the one with the more complete Context/Approach (or the lower id if tied), archive the other to `done/` via `~/.claude/skills/close/complete-todo.ps1 -Id <id>` (never plain-delete, per the contract's Release rule). List every archive: `archived <id>-<slug>.md - duplicate of <id>-<slug>.md`. If none found, say "No duplicates found."

## Step 3 - Classify

Read each file. Check PRODUCT first - it overrides EASY/HARD when it applies. Label as PRODUCT, EASY, or HARD:

| Label | Criteria |
|-------|----------|
| PRODUCT | Adds, removes, or alters user-facing functionality or behavior, OR the file carries a `Type: product-change` header (authoritative when present - don't re-litigate) |
| EASY | Self-contained: single file or tightly scoped, no open design questions, no external service calls, no new decisions required, acceptance criteria is clear |
| HARD | Anything else: multi-file, open design question, external service, requires dev input before starting |

When in doubt between EASY and HARD, label HARD. PRODUCT todos are never auto-executed and never
enter the HARD queue's "important" urgency ranking (step 7) - they're only offered when Joe
explicitly says he's doing product work.

## Step 4 - Dry-run confirmation

Show the classification before touching anything, as a clear standalone report. This is a
**deliverable Joe must read** before approving, so it MUST be delivered correctly:

- **Do NOT wrap it in, or precede it with, an `AskUserQuestion` call** - same-turn AUQ erases prior text for Joe's client; see `/rate-it`'s house pattern for why.
- Emit the report as the turn's **FINAL message with no tool call after it**, then stop and wait for
  Joe's plain-text reply.

The report has four parts:

**1. Dedupe result** - the `archived <id> - duplicate of <id>` lines from step 2, or "No duplicates found."

**2. EASY set** - a markdown table, one row per EASY todo, so Joe can see at a glance what each one
touches. Do not just list filenames:

```
### EASY - will auto-execute in id order (each verified first, then `/commit`)

| id | What it does | Area / files touched | Why EASY |
|----|--------------|----------------------|----------|
| 99 | CountModal title truncates via CSS instead of a hardcoded 20-char JS cap | `frontend/src/components/CountModal.tsx` | one component, clear acceptance, no decision |
| 111 | Remove the dead `toggleTheme` export | `frontend/src/hooks/useTheme.ts` | single-file dead-code drop |
```

Keep "What it does" to one plain sentence and "Why EASY" to a short phrase. If a listed todo has an
active, non-stale claim in `.claims/` (per the contract), add ` [claimed by another session - will
skip]` in its row.

**3. PRODUCT set** - a compact count plus the ids and one-line descriptions, listed separately from
EASY/HARD so they never read as actionable in this pass (e.g. "3 PRODUCT todos parked - not
auto-executed, not in the HARD queue: `04` wire-or-hide the Approve Orders button, ..."). Offered
only when Joe explicitly says he's doing product work, never picked up from this report.

**4. HARD queue** - a compact count plus the ids, so Joe knows what's parked without a wall of text
(e.g. "62 HARD todos parked for step 7 - refactors, IA/design, tooling/CI, external-service, and
decision todos"). The full pickable list comes later, in step 7.

Then close the message with a plain-text prompt (NOT a tool call):

> Reply **run it** to execute the EASY batch, **reclassify `<id>`** to move a todo between EASY/HARD
> first, or **cancel** to stop. Nothing is touched until you reply.

On Joe's reply: `run it` -> step 5; `reclassify <id>` -> update the label, re-emit the report, wait
again; `cancel` -> stop, no changes.

## Step 5 - Evaluate EASY todos before executing

**Reference-point check, before dispatch.** Resolve trunk (repo's own convention, e.g.
`GIT_FLOW.md`; default `develop` then `main`), then compute and PRINT
`git rev-list --left-right --count HEAD...origin/<trunk>`. If behind is `0`, the checkout matches
trunk - no further ceremony. If behind is nonzero, the dispatch prompt below MUST state the
ahead/behind numbers and instruct the subagent to cite evidence via `git show origin/<trunk>:<path>`
rather than the working copy, naming which ref each citation came from - a todo can be DONE or MOOT
on trunk while its premise still reads valid against a stale checkout.

Dispatch ONE read-only subagent (`model: 'sonnet'`, per the global subagent rule) that reads every EASY todo in full and verifies its premise against the reference point resolved above - still valid? actually easy? any downgrade risk (hidden design question, stale assumption, feature that's really HARD)? It returns one verdict per todo with a one-line evidence note, stating which ref the evidence came from. Paste the canonical preamble from `refs/builder-preamble.md` into the dispatch prompt (it's read-only, so the `READ-ONLY DISPATCH` opt-out applies) - `hooks/dispatch-preamble-guard.py` rejects a prompt missing its markers.

- **DO** - premise holds, proceed to execution.
- **SKIP** - already done, stale, or superseded. Move to `done/` (create if missing), prune its PLAN.md line, note the evidence; do not execute.
- **FLAG** - real downgrade or open question found. Report it to the dev; re-queue as HARD instead of auto-executing.

Show the DO/SKIP/FLAG breakdown before proceeding to step 6.

## Step 6 - Execute EASY todos

**Claim the whole DO-verdict set in one call before executing any of them**, per the contract's
batch-claim form: `claim-todo.ps1 -Id <id1>,<id2>,...` in id order. Handling N todos this way costs
one remembered claim call, not N. Any id the batch reports as lost to a live session (exit 1, named
in its per-id line) is dropped from this run with a note; ids that hit a genuine error (exit 2) are
surfaced and dropped the same way.

For each remaining **DO**-verdict EASY todo, in id order:

1. Read the full file. Announce which todo is starting (id + title).
2. Execute the task fully. Touch the claim file's mtime after major steps (heartbeat).
3. Run `~/.claude/skills/close/complete-todo.ps1 -Id <id> -Note "completed, commit <sha>"` to
   append the Notes line, move the todo to `done/`, prune its PLAN.md line, and release the claim
   in one call. Fall back to doing those steps by hand per the contract if the helper is
   unavailable (non-Windows, or missing).
4. `/commit` - invoke and read the skill in full only for this run's first commit; every commit
   after that follows `/commit`'s procedure directly (session marker already written, prefilters,
   pathspec form, branch/overlap checks all still apply) without re-invoking the skill file.

If a todo hits a blocker: release its claim, surface the blocker, stop that todo, continue with the next EASY.

## Step 7 - Surface HARD todos

PRODUCT todos never appear here, in any urgency tier - they were already parked separately in step
4 and stay out of this "important todos that need doing" ranking entirely.

Before rendering, skim each HARD todo (title + Goal only, not a full triage pass) and assign an
urgency read: **High** (blocking, time-sensitive, or the dev's own prior notes flag it urgent),
**Med** (normal backlog), **Low** (nice-to-have). Also flag any todo that looks done/stale/superseded
per those same notes as a delete candidate. This is a quick skim, not a dedicated triage subagent -
only escalate to that if the dev explicitly asks what's urgent (mirrors step 5's cost discipline).

Once all EASY todos are done (or if none existed), present the HARD queue the same way as step 4 -
as the turn's **FINAL message with no tool call after it**, never buried in an `AskUserQuestion`
(same reason: pre-tool text is invisible to Joe). Render it as a table, ordered High -> Med -> Low
(id order within a tier) so the full list is readable, not capped at 4:

```
### HARD - pick one to tackle next (`/pickup <id>` or just name it)

| id | What it does | Area | Urgency |
|----|--------------|------|---------|
| ...one row per HARD todo, High first... | | | High / Med / Low, + "delete candidate?" if flagged |
```

Close with a plain-text prompt: "Name an id to execute it inline now, or say done to stop." On reply:
a chosen id -> execute inline (same flow as step 6, claim included); done/skip -> stop and leave the
HARD ids listed as the reminder.

## Unattended runs

Under `/autopilot` or an explicit no-input instruction, the invoking message itself counts as
`run it` for Step 4: the dry-run report still prints, then execution proceeds straight to Step 5
without waiting for a reply. Step 5's `FLAG` verdicts still re-queue as HARD rather than being
auto-answered - unattended mode changes the Step 4 gate only, not the FLAG/HARD judgment call.

## Notes

- Source of truth: `.claude/todos/` only.
- This skill executes in id order regardless of PLAN.md ordering - plan-ordered execution is `/pickup`'s job. It still prunes PLAN.md lines of todos it completes.
- Never commit directly. `/commit` is invoked and read in full once per run; every completed todo's
  commit after that follows its procedure directly.
