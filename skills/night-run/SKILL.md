---
name: night-run
description: Triggers on /night-run only. Schedules a queue of REMOTE overnight agents via RemoteTrigger that grind through plan files in docs/night_run/. PC can be turned off. For local (PC must stay on) use /cron-run.
argument-hint: "<count|all> [every] <interval> [till HH[AM|PM]]"
---

# /night-run

> Schedule overnight agents to work plan files remotely on Anthropic's cloud (PC can be off), one task at a time, with review and side-branch failure isolation.

## Prerequisites

Refuse with a clear message if any check fails:

1. Inside a git repo (`git rev-parse --is-inside-work-tree`)
2. Working tree clean (`git status --porcelain` empty)
3. `docs/night_run/plans/` exists and has at least one `.md` plan file
4. Repo has a GitHub remote (`git remote get-url origin` returns a github.com URL) - the remote agent must be able to clone and push

## Step 1 - Parse arguments

Free-form. Tokens may appear in any order:

- count: `all` or positive integer
- interval: regex `(every )?(\d+)(m|min|h|hr)` (example: `30m`, `every 1h`, `90min`, `2hr`)
- end cap (optional): regex `(till|until) (\d{1,2})(:\d{2})?(am|pm)?` (case-insensitive). If no am/pm and hour <= 12, assume the next occurrence (so `till 1PM` after midnight means 13:00 today; `till 7AM` at 11PM means 07:00 tomorrow).

Reject and ask for missing pieces if count or interval is absent.

## Step 2 - Build INDEX.md

- Read current branch via `git rev-parse --abbrev-ref HEAD`
- Read git remote URL via `git remote get-url origin`. Normalize to `https://github.com/owner/repo` (no `.git` suffix).
- Glob `docs/night_run/plans/*.md`. Title for each = first `# ` heading or filename without extension
- If `docs/night_run/INDEX.md` exists, preserve `[x]` and `[!]` lines from the prior run by plan path. New plans get `[ ]`.
- unfinished = count of `[ ]` lines after merge
- If count argument is integer, treat unfinished as min(unfinished, count)
- firings = ceil(unfinished * 1.1) (10% buffer, minimum +1 if unfinished > 0)
- If end cap given: firings = min(firings, floor((end_cap - now) / interval))
- Write INDEX.md (format below)
- Commit and push INDEX.md now so the remote agent sees it: `git add docs/night_run/INDEX.md`, then commit with message `night-run: init INDEX`, then push.

## Step 3 - Schedule remote agents

Load `RemoteTrigger` via ToolSearch first.

For n in 0..firings-1:

- slot_time = now + (n + 1) * interval (convert to UTC RFC3339 for `run_once_at`)
- Build the self-contained tick prompt (template below) substituting actual values
- Generate a fresh lowercase UUID v4 for `events[].data.uuid`
- Call `RemoteTrigger` with:

```json
{
  "action": "create",
  "body": {
    "name": "night-run-tick-<n+1>-of-<firings>",
    "run_once_at": "<slot_time_utc>",
    "enabled": true,
    "job_config": {
      "ccr": {
        "environment_id": "env_01WbN3tVvAW5TjieuFJeW2cx",
        "session_context": {
          "model": "claude-sonnet-4-6",
          "sources": [
            {"git_repository": {"url": "<repo_url>"}}
          ],
          "allowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Agent"]
        },
        "events": [
          {
            "data": {
              "uuid": "<generated_uuid>",
              "session_id": "",
              "type": "user",
              "parent_tool_use_id": null,
              "message": {
                "content": "<tick_prompt>",
                "role": "user"
              }
            }
          }
        ]
      }
    }
  }
}
```

- Track returned routine IDs for the summary

## Step 4 - Print summary

Show:

- branch and repo URL
- interval
- firings count + buffer count
- first and last fire time (local timezone)
- relative path to INDEX.md
- list of created routine IDs with links: `https://claude.ai/code/routines/<id>`
- note: PC can be turned off - agents run on Anthropic's cloud

## Tick prompt template

Substitute `<BRANCH>`, `<REPO_URL>`, and `<INTERVAL_MINUTES>` before embedding in the JSON.

```
You are executing a night-run tick on this repository. Work autonomously - no user is present.

Repository: <REPO_URL>
Branch: <BRANCH>
Interval (minutes): <INTERVAL_MINUTES>

## Instructions

### 1. Reclaim stale locks
Read `docs/night_run/INDEX.md`. For each `[~ HH:MM]` line, compute minutes since that timestamp. If older than `<INTERVAL_MINUTES> * 2` minutes, rewrite that line to `[ ]`.

### 2. Pick next task
Find the first `[ ]` line in `docs/night_run/INDEX.md`. If none exist, output "night-run: all tasks done" and stop.

### 3. Soft-lock the task
Rewrite the chosen `[ ]` to `[~ HH:MM]` using current UTC time (HH:MM zero-padded). Stage and commit:
- `git add docs/night_run/INDEX.md`
- `git commit -m "night-run: lock <slug>"`
- `git push`

### 4. Verify branch
Run `git rev-parse --abbrev-ref HEAD`. If not `<BRANCH>`, run `git checkout <BRANCH>`. If that fails, mark `[!]` on the task with reason `branch mismatch`, commit + push INDEX update, stop.

### 5. Execute the plan
Read the linked plan file. If the plan has 5+ independent tasks, use the Agent tool (subagent-driven). Otherwise execute inline. Apply every change the plan describes.

### 6. Review subagent
Dispatch a fresh general-purpose Agent subagent with this exact brief:
"Cold review of the current uncommitted diff against HEAD. The plan being implemented is at <plan-path>. Look for: bugs, unsafe patterns, missed edge cases, broken or missing tests, scope creep beyond the plan, security issues. Report issues as a numbered list with severity tags BLOCKER, WARN, or NIT. Do not edit any files. Be thorough - this code lands unsupervised."

### 7. Fix loop
If review has any BLOCKER: apply targeted fixes, re-dispatch the review subagent. Repeat up to 4 total attempts (1 initial + 3 retries). WARN and NIT do not trigger retry - capture them in the commit body.

### 8a. Success (no BLOCKER)
- `git add -A`
- `git commit -m "<plan slug>: <one-line summary>" -m "<WARN/NIT list if any>"`
- `git push`
- Rewrite `[~ HH:MM]` to `[x]` in INDEX.md
- `git add docs/night_run/INDEX.md`
- `git commit -m "night-run: complete <slug>"`
- `git push`

### 8b. Failure (BLOCKER after 4 attempts)
- `git checkout -b night-run/failed-<slug>`
- `git add -A`
- `git commit -m "WIP: night-run failed <slug>" -m "<last review summary>"`
- `git push -u origin night-run/failed-<slug>`
- `git checkout <BRANCH>`
- `git restore .`
- `git clean -fd`
- Rewrite `[~ HH:MM]` to `[!] <slug> (side: night-run/failed-<slug>)` in INDEX.md
- `git add docs/night_run/INDEX.md`
- `git commit -m "night-run: failed <slug>"`
- `git push`

### 9. Log the run
Append one line to `docs/night_run/log.md` (create with `# Night Run Log` header if missing):
`<YYYY-MM-DD HH:MM UTC> <[x]|[!]> <slug> attempts=<N>`
- `git add docs/night_run/log.md`
- `git commit -m "night-run: log <slug>"`
- `git push`
```

## INDEX.md format

```
# Night Run - YYYY-MM-DD

Branch: <branch>
Repo: <repo_url>
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

- Each tick is a fully isolated remote CCR session. No shared state between ticks - INDEX.md is the only coordination mechanism.
- The remote agent does NOT have the `/commit` skill. All commits use raw git commands.
- `run_once_at` supports sub-hour intervals (unlike `cron_expression` which requires minimum 1 hour).
- The dev can run `/cron-run tick` manually for a local dry-run before setting up the remote run.
- If the end cap forces fewer firings than tasks, the summary clearly states `<X tasks won't fit in window>`.
- Routine links: `https://claude.ai/code/routines/<id>` - visit to cancel if needed.
- The repo must be public OR the CCR environment must have GitHub auth configured for private repos.
