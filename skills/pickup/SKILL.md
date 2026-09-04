---
name: pickup
description: Claims and executes the next unclaimed PLAN.md item, running its Verify commands first. --merge collapses several outstanding handoffs into one reconciled brief.
disable-model-invocation: true
argument-hint: "[--unattended] [--merge [<id>,<id>,...]] [<id> to pick a specific todo]"
---

# /pickup

> Pull the next planned todo off the lane, claim it, and do it.

All mechanics (PLAN.md schema, claim protocol, heartbeat, staleness, done/, pruning, git policy)
live in `~/.claude/skills/close/ai-todos-format.md` - follow that contract exactly.

## Mode

Interactive by default. `--unattended` is passed ONLY by non-interactive callers (autopilot,
scheduled runs) - never inferred. `--merge` switches to Merge mode (below) instead of Step 1's
single-select. The two combine (`--unattended --merge <id>,<id>`) only with explicit ids - see
Merge mode Step M1 for why unattended auto-detection is refused.

## Step 1 - Select

Read `.claude/todos/PLAN.md`, pruning vanished ids per the contract.

- `--merge` was passed: skip this whole step and go to Merge mode below instead.
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

Claim the id in the same tool call that starts Step 3's read, per the contract's "side effect of
the call that starts the work" rule - e.g. `claim-todo.ps1 -Id <id>; Get-Content <path>` as one
PowerShell invocation, never claim-todo.ps1 run alone as a preceding step. Lost the race to a live
session: go back to Step 1 for the next line.

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

Decide which of the two endings applies per `close/ai-todos-format.md`'s "Two endings, and the tell
that picks between them" - Completed versus Advanced but not finished, decided against the todo
file rather than against how the session felt. That contract owns the rule and every executor obeys
it; it is not restated here.

Then run `/commit` if the work produced changes, and name any remaining work explicitly in the
completion summary. `--unattended` runs get no exemption from either ending.

Finish by naming the next item on the lane (or "lane empty") so the dev knows what another
`/pickup` would grab.

## Merge mode (`--merge`)

Collapses several outstanding handoff todos into one reconciled brief, per
`.claude/todos/457-merge-several-sessions-into-one-via-handoffs.md`'s Approach. This section only
covers what happens before a normal pickup starts - Step M5 falls through to Steps 3-7 above
unchanged, run once against the merged brief this section produces instead of N times against
the sources.

### Step M1 - Identify the set

Two forms:

- **Explicit** - `--merge <id>,<id>,...`. The dev names the ids directly. Always safe, use this
  form whenever it's available.
- **Auto-detect** (`--merge` with no ids, interactive only) - a todo is a merge CANDIDATE when it
  has all five of Handoff mode's sections (Goal/Context/Approach/Verify/Notes), `**Origin:**
  dev`, and sits in the contiguous run of ids at the TOP of PLAN.md (Handoff mode always prepends
  new handoffs there). This is a heuristic, not a guarantee - `ai-todos-format.md`'s Handoff mode
  has no explicit machine-checkable marker distinguishing a handoff from any other dev/task todo
  yet, and adding one belongs to that file, not this skill. **Always confirm the detected
  candidate list with the dev via one `AskUserQuestion` before claiming anything** - never merge
  on a silent guess. Fewer than two candidates: drop back to Step 1's normal single-select, no
  merge happens.
- **`--unattended --merge` with no explicit ids** - auto-detection needs a confirmation round
  unattended has nobody to answer. Log a blocker per the caller's blocker-log convention
  (autopilot: `.for_bepy/autopilot-logs/<slug>.md`) and stop; never guess the set unattended.

### Step M2 - Claim the whole set

Claim every target id in ONE `claim-todo.ps1` batch call (the contract's batch form), never one
call per id. Per Acceptance, a partial claim aborts the whole merge - it never silently proceeds
with the subset that succeeded:

- Exit 0 (every id claimed): continue to Step M3.
- Exit 1 or 2 (any id lost to a live claim, or a genuine error): release every id this call just
  claimed (delete its `.claims/<id>.claim`), report which id(s) blocked it and why, and stop the
  merge entirely. Do not fall back to picking just one of them - that is a smaller, different task
  the dev didn't ask for on this invocation.

### Step M3 - Reconcile into one brief

Read every claimed todo file in full. Reserve a fresh id (`reserve-todo-id.ps1`, same as any
other backlog write) and write ONE new todo that becomes the merge's working brief:

- `**Type:** task`, `**Origin:** dev` (it still records the dev's own in-flight work).
- **Goal** - the union of what the dev is trying to achieve across the merged sessions.
- **Context** - what each session tried, in what order, where each stalled; name which source id
  each fact came from so a contradiction stays traceable back to its origin.
- **Approach** - the reconciled next steps: what ALL sources agree on, folded once; what only one
  knew, kept and attributed to it. Where two sources genuinely CONTRADICT each other, that goes in
  `## Open questions` instead, never silently resolved by picking one side.
- **Verify** - the union of every source's Verify commands, de-duplicated, `git pull` first.
- **Notes** - carry forward any open decision a source still owed an answer on.
- `## Open questions` - one entry per contradiction found above, tagged `[ARCH]` (or whichever
  domain fits) exactly like any other open decision, so Step 4's existing decisions gate below
  picks it up with no new mechanism.

Reference every source id by number in Context. Add `<!-- duplicate-checked -->` up front - a
merged brief predictably shares vocabulary with the sources it just read and would otherwise trip
`hooks/todo-duplicate-guard.py` against them. Prepend it to PLAN.md per Handoff mode's own PREPEND
convention (newest next).

### Step M4 - Archive the sources

For each merged id, run `~/.claude/skills/close/complete-todo.ps1 -Id <id> -Note "folded into
<new-id>"` - never a hand-rolled `Move-Item` loop. This is the existing Completed ending
(`close/ai-todos-format.md`'s "Two endings"), not a new third one: the dev's 2026-09-04 decision
settled the source todo's one open question as move-to-`done/`, matching every other executor,
rather than a genuine delete. The helper's `-Note` records the audit trail in the same call that
moves the file, prunes its PLAN.md line, and releases its claim.

### Step M5 - Continue as a normal pickup

Fall through to Step 3 (Brief) using the NEW merged todo exactly as if it were the id Step 1 had
selected. Steps 4-7 run unchanged, including Step 4's decisions gate over the `## Open questions`
block Step M3 wrote - that is where a contradiction actually reaches the dev.

A single outstanding handoff never reaches Merge mode at all (Step M1 needs two or more
candidates before anything happens) - `/pickup` with no flags behaves exactly as it does today.

## Notes

- One todo per invocation. Chain-run sessions call `/pickup` again for the next item.
- On any abort path, ALWAYS release the claim - never leave a lock for work that isn't happening.
