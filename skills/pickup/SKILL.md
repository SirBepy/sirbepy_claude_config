---
name: pickup
description: Claims and executes the next unclaimed PLAN.md item, running its Verify commands first.
disable-model-invocation: true
argument-hint: "[--unattended] [<id> to pick a specific todo]"
---

# /pickup

> Pull the next planned todo off the lane, claim it, and do it.

All mechanics (PLAN.md schema, claim protocol, heartbeat, staleness, done/, pruning, git policy)
live in `~/.claude/skills/close/ai-todos-format.md` - follow that contract exactly.

## Mode

Interactive by default. `--unattended` is passed ONLY by non-interactive callers (autopilot,
scheduled runs) - never inferred.

## Step 1 - Select

Read `.claude/todos/PLAN.md`, pruning vanished ids per the contract.

- If an explicit `<id>` arg was given: that's the pick (it doesn't need a PLAN.md line).
- If args were given but aren't a bare id (free text): check whether they plausibly match an
  existing backlog item by slug or title. A match - confirm it in one line before proceeding
  ("this looks like todo NN - <title>, continuing with that?"). No match - do not infer a target
  from the git branch, project memory, or working-tree state; state plainly that the args don't
  correspond to any backlog item and ask what to do via `AskUserQuestion`.
- Otherwise (no args): the first plan line, top to bottom, whose id has no active (non-stale)
  claim in `.claims/`. Claimed-by-a-live-session lines are skipped with a one-line note.
- No PLAN.md or an empty lane: say so, list up to 5 unplanned backlog ids + titles, and stop
  (planning is `/plan-todos`'s job).

## Step 2 - Claim

Claim the id per the contract's protocol (temp file + no-overwrite rename, Windows retry
caveat, stale-claim reclaim rule). Lost the race to a live session: go back to Step 1 for the
next line.

## Step 3 - Brief

Read the todo file in full. Print a 2-4 sentence summary of Goal + where things stand (for
handoff todos, this is the "what happened last session" recap).

## Step 4 - Decisions gate

If the todo records open decisions (in `## Notes` or elsewhere):

- **Interactive:** surface them in ONE AskUserQuestion before any work.
- **`--unattended`:** proceed using only decisions the todo records as already resolved. If an
  unresolved decision blocks the work, write the blocker per the caller's blocker-log convention
  (autopilot: `.for_bepy/autopilot-logs/<slug>.md`), release the claim, and stop this todo -
  never guess, never silently skip the decision.
- **Card still pending, dev sends an unrelated or non-answering message** (`continue`, `go`, a
  question about something else, no answers to the open decisions): this is NOT the timeout case
  and NOT permission to proceed on recommendations - the card is still alive. Re-send the card, or
  ask which of the pending decisions to skip. Distinguish mechanically, not by judgment: only an
  actual MCP idle-timeout error means the card died. No error means it is still pending.
- **Card timed out mid-run** - REQUIRES an actual MCP idle-timeout error as its precondition (an
  interactive question died unanswered - `sent no response or progress` /
  `CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT`, ~45 min of dead wall clock, the dev walked away). Absent
  that error, the card never died - use the still-pending branch above instead. This is a TOOL
  ERROR, not a "no", and not a signal to abandon the todo.
  - An option is explicitly badged/labelled recommended AND the resulting action is reversible (a
    code change; never a deploy, push, or destructive/outward-facing op) - proceed on it.
  - No option is marked recommended, or the decision is high-stakes or hard to reverse - stop and
    park the work, same as the unattended blocker path above.
  - Either way, report the auto-taken (or parked) decision prominently in the completion summary,
    with an explicit offer to redo it - never let it read as though it were actually answered.
  - Do not plan on a "recovery" tool to resume the same card; it may not exist in this session.

## Step 5 - Verify

If the todo has a `## Verify` section: execute each `- [ ]` item in order as real commands or
inspections. Do not just print them. A failing verify item is a blocker: surface it (or log it
unattended), release the claim, stop.

## Step 6 - Execute

Do the task per the todo's Approach/Acceptance. Touch the claim file's mtime after major steps
(heartbeat). Follow all global rules (`/commit` only via the skill, testing floor, etc.).

## Step 7 - Complete

First decide which outcome applies. The tell is decidable, not a judgement call: check it against
the todo file, not against how the session felt.

- **Completed** - every `## Acceptance` item is satisfied, and the Goal does not name an epic or
  multi-ticket outcome.
- **Advanced but not finished** - either the Goal names an epic/multi-ticket outcome, or one or
  more `## Acceptance` items are still unmet and this session did not (or could not) address them.
  Real work can still have landed; that alone never makes it "Completed".

**Completed:** run `~/.claude/skills/close/complete-todo.ps1 -Id <id>` to move the todo to
`done/`, prune its PLAN.md line, and release the claim in one call. Fall back to the contract's
manual three-step sequence if the script is unavailable. Then run `/commit` if the work produced
changes.

**Advanced but not finished:** do NOT move the todo to `done/` and do NOT run
`complete-todo.ps1`. Instead: update the todo file with what changed this session, refresh its
PLAN.md line so the lane reflects the new state (re-read PLAN.md first per its CAS edit
discipline), then release the claim (delete `.claims/<id>.claim`) - the todo stays planned for a
future `/pickup`. Run `/commit` if the work produced changes. Name the remaining work explicitly
in the completion summary. `--unattended` runs follow the same rule: never archive a todo with
unmet Acceptance items just because the run reached Step 7.

Finish by naming the next item on the lane (or "lane empty") so the dev knows what another
`/pickup` would grab.

## Notes

- One todo per invocation. Chain-run sessions call `/pickup` again for the next item.
- On any abort path, ALWAYS release the claim - never leave a lock for work that isn't happening.
