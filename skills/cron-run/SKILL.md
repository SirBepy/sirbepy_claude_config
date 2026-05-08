---
name: cron-run
description: Triggers on /cron-run only. Schedules a queue of LOCAL overnight agents using CronCreate that grind through plan files in docs/night_run/, with inline review subagents and side-branch failure isolation. PC must stay on. For remote (PC off) use /night-run.
argument-hint: "<count|all> [every] <interval> [till HH[AM|PM]]"
---

# /cron-run

> Schedule overnight agents to work plan files locally via CronCreate, one task at a time, with review and side-branch failure isolation. PC must stay on and Claude Code must remain open.

## Modes

The first argument selects the mode:

- `tick` -> single task cycle (cron fires this; never run by the dev)
- anything else -> schedule mode (the dev runs this)

## Prerequisites (schedule mode only)

Refuse with a clear message if any check fails:

1. Inside a git repo (`git rev-parse --is-inside-work-tree`)
2. Working tree clean (`git status --porcelain` empty)
3. `docs/night_run/plans/` exists and has at least one `.md` plan file

## Schedule mode

### 1. Parse arguments

Free-form. Tokens may appear in any order:

- count: `all` or positive integer
- interval: regex `(every )?(\d+)(m|min|h|hr)` (example: `30m`, `every 1h`, `90min`, `2hr`)
- end cap (optional): regex `(till|until) (\d{1,2})(:\d{2})?(am|pm)?` (case-insensitive). If no am/pm and hour <= 12, assume the next occurrence (so `till 1PM` after midnight means 13:00 today; `till 7AM` at 11PM means 07:00 tomorrow).

Reject and ask for missing pieces if count or interval is absent.

### 2. Build INDEX.md

- Read current branch via `git rev-parse --abbrev-ref HEAD`
- Glob `docs/night_run/plans/*.md`. Title for each = first `# ` heading or filename without extension
- If `docs/night_run/INDEX.md` exists, preserve `[x]` and `[!]` lines from the prior run by plan path. New plans get `[ ]`.
- unfinished = count of `[ ]` lines after merge
- If count argument is integer, treat unfinished as min(unfinished, count)
- firings = ceil(unfinished * 1.1) (10% buffer, minimum +1 if unfinished > 0)
- If end cap given: firings = min(firings, floor((end_cap - now) / interval))
- Write INDEX.md (format below)

### 3. Schedule crons

For n in 0..firings-1:

- slot_time = now + (n + 1) * interval
- If slot_time minute is :00 or :30, shift by +3 minutes (per CronCreate fleet jitter guidance)
- Build cron: `<M> <H> <DoM> <Month> *` pinned to slot_time
- CronCreate(cron, recurring=false, durable=true, prompt=`/cron-run tick`)
- Track returned IDs in memory for the summary

### 4. Print summary

Show:

- branch
- interval
- firings count + buffer count
- first and last fire time
- relative path to INDEX.md
- reminder: keep Claude Code open and PC awake through the run

## Tick mode

### 1. Reclaim stale locks

Read `docs/night_run/INDEX.md`. For each `[~ HH:MM]` line, compute `now - HH:MM`. If older than `2 * interval`, rewrite that line back to `[ ]`. The interval comes from the `Interval:` header in INDEX.md.

### 2. Pick next task

First `[ ]` line in document order. If none, print "cron-run: all tasks done" and exit cleanly.

### 3. Soft-lock the task

Rewrite the chosen `[ ]` to `[~ HH:MM]` (current local time, zero-padded). Stage, then invoke `/commit` for the INDEX.md change. Push.

### 4. Verify branch

Compare `git rev-parse --abbrev-ref HEAD` to the `Branch:` value in INDEX.md.

- If equal, continue.
- If not equal, attempt `git checkout <branch>`. If that fails (dirty tree, missing branch), mark `[!]` on the task with reason `branch mismatch`, commit + push INDEX update, exit.

### 5. Execute the plan

Read the linked plan file. Decide subagent-driven vs inline per CLAUDE.md "Subagent-Driven vs Inline Execution" rule. Execute.

### 6. Review subagent

Dispatch a fresh subagent (general-purpose) with this brief:

> Cold review of the current uncommitted diff against HEAD. The plan being implemented is at `<plan-path>`. Look for: bugs, unsafe patterns, missed edge cases, broken or missing tests, scope creep beyond the plan, security issues. Report issues as a numbered list with severity tags BLOCKER, WARN, or NIT. Do not edit any files. Be thorough; this code lands unsupervised.

### 7. Fix loop

If review reports any BLOCKER:

- Apply targeted fixes addressing each BLOCKER
- Re-dispatch the review subagent
- Repeat up to 4 total attempts (1 initial + 3 retries)

WARN and NIT do not trigger a retry. Capture them in the commit body.

### 8a. Success path (clean review with no BLOCKER)

- Invoke `/commit` for the work
- Push
- Rewrite `[~ HH:MM]` to `[x]` in INDEX.md
- Invoke `/commit` for the INDEX update, push

### 8b. Failure path (BLOCKER still present after 4 attempts)

- slug = kebab-case of plan filename without extension
- `git checkout -b night-run/failed-<slug>`
- Stage all current work, invoke `/commit` with subject `WIP: night-run failed <slug>` and body containing the last review summary
- Push the side branch with `-u`
- `git checkout <original-branch>` (recorded from INDEX header)
- Safety net: `git restore .` then `git clean -fd`
- Rewrite `[~ HH:MM]` to `[!]` in INDEX.md and append ` (side: night-run/failed-<slug>)`
- Invoke `/commit` for INDEX update, push

### 9. Log the run

Append one line to `docs/night_run/log.md` (create with `# Night Run Log` header if missing):

```
<YYYY-MM-DD HH:MM> <[x]|[!]> <slug> attempts=<N>
```

### 10. Orphan check before exit

Run the project orphan-check per CLAUDE.md "Process Hygiene". Kill any node orphans before returning.

## INDEX.md format

```
# Night Run - YYYY-MM-DD

Branch: <branch>
Interval: <interval>
Scheduled: <N> (<unfinished> tasks + <buffer> buffer)
Started: HH:MM
End cap: <HH:MM | none>

## Tasks

- [ ] <title> - @docs/night_run/plans/<file>.md
- [~ HH:MM] <title> - @docs/night_run/plans/<file>.md
- [x] <title> - @docs/night_run/plans/<file>.md
- [!] <title> - @docs/night_run/plans/<file>.md (side: night-run/failed-<slug>)
```

## Notes

- Cron entries are `durable: true` so they survive Claude Code restarts, but only fire while Claude Code is open and idle. Keep Claude Code running and PC awake.
- All commits go through `/commit`. Never bypass.
- The dev can run `/cron-run tick` manually to dry-run a single cycle before walking away.
- INDEX.md is the only source of truth across ticks. Each tick is a fresh session with no inherited state.
- If `unfinished * 1.1` rounds down to the same integer, force at least +1 firing as buffer.
- If the end cap forces fewer firings than tasks, the summary clearly states `<X tasks won't fit in window>`.
