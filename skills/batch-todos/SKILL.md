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

For each duplicate pair: keep the one with the more complete Context/Approach (or the lower id if tied), delete the other and prune its PLAN.md line if present. List every deletion: `deleted <id>-<slug>.md - duplicate of <id>-<slug>.md`. If none found, say "No duplicates found."

## Step 3 - Classify

Read each file. Label as EASY or HARD:

| Label | Criteria |
|-------|----------|
| EASY | Self-contained: single file or tightly scoped, no open design questions, no external service calls, no new decisions required, acceptance criteria is clear |
| HARD | Anything else: multi-file, open design question, external service, requires dev input before starting |

When in doubt, label HARD.

## Step 4 - Dry-run confirmation

Show the classification before touching anything, as a clear standalone report. This is a
**deliverable Joe must read** before approving, so it MUST be delivered correctly:

- **Do NOT wrap it in, or precede it with, an `AskUserQuestion` call.** Joe's client does not
  render text emitted before/around a tool call (see memory `feedback-no-text-before-question-tool`
  and todo 80) - a same-turn AUQ erases this report and buries the choice. This gate deliberately
  overrides the global "every question via AskUserQuestion" rule, exactly as `/rate-it` does.
- Emit the report as the turn's **FINAL message with no tool call after it**, then stop and wait for
  Joe's plain-text reply.

The report has three parts:

**1. Dedupe result** - the `deleted <id> - duplicate of <id>` lines from step 2, or "No duplicates found."

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

**3. HARD queue** - a compact count plus the ids, so Joe knows what's parked without a wall of text
(e.g. "62 HARD todos parked for step 7 - refactors, IA/design, tooling/CI, external-service, and
decision todos"). The full pickable list comes later, in step 7.

Then close the message with a plain-text prompt (NOT a tool call):

> Reply **run it** to execute the EASY batch, **reclassify `<id>`** to move a todo between EASY/HARD
> first, or **cancel** to stop. Nothing is touched until you reply.

On Joe's reply: `run it` -> step 5; `reclassify <id>` -> update the label, re-emit the report, wait
again; `cancel` -> stop, no changes.

## Step 5 - Evaluate EASY todos before executing

Dispatch ONE read-only subagent (`model: 'sonnet'`, per the global subagent rule) that reads every EASY todo in full and verifies its premise against the current tree - still valid? actually easy? any downgrade risk (hidden design question, stale assumption, feature that's really HARD)? It returns one verdict per todo with a one-line evidence note:

- **DO** - premise holds, proceed to execution.
- **SKIP** - already done, stale, or superseded. Move to `done/` (create if missing), prune its PLAN.md line, note the evidence; do not execute.
- **FLAG** - real downgrade or open question found. Report it to the dev; re-queue as HARD instead of auto-executing.

Show the DO/SKIP/FLAG breakdown before proceeding to step 6.

## Step 6 - Execute EASY todos

For each **DO**-verdict EASY todo in id order:

1. **Claim it** per the contract's claim protocol. If the claim is lost to a live session, skip with a note and continue.
2. Read the full file. Announce which todo is starting (id + title).
3. Execute the task fully. Touch the claim file's mtime after major steps (heartbeat).
4. Append a Notes line to the todo recording what happened (completed + commit sha), then run
   `~/.claude/skills/close/complete-todo.ps1 -Id <id>` to move it to `done/`, prune its PLAN.md
   line, and release the claim in one call. Fall back to doing those three steps by hand per the
   contract if the helper is unavailable (non-Windows, or missing).
5. Run `/commit` after each completed todo.

If a todo hits a blocker: release its claim, surface the blocker, stop that todo, continue with the next EASY.

## Step 7 - Surface HARD todos

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
- Never commit directly. Always use `/commit` after each completed todo.
