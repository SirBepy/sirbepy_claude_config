<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=8, reconfirm-count=2, content-hash=649e582b -->
# Upgrade /delegate to detect dead or stalled background subagents

**Type:** skill-improvement
**Origin:** ai

## Goal

`/delegate` should notice when a dispatched background subagent has died and surface it, instead of leaving the main agent parked on `<cc-status:working>` indefinitely waiting for a completion notification that will never arrive.

## Context

Incident 2026-07-28 (zng-app, partner service-fee audit). The main agent dispatched 4 background scouts in one turn. One returned normally. The other 3 died silently: no completion notification, no error, nothing. The main agent reported `working` and sat idle for **2 hours 15 minutes** until Joe asked "its been 2 hours, r they still not done?".

Joe's words: "deffo a mistake, when we do close, make sure to remember in a todo in the global .claude folder that we gotta upgrade the delegate skill to handle this better".

Key detail: the harness explicitly tells the main agent "You will be notified automatically when it completes" and "do not report, assume, or predict them". That phrasing encourages the agent to trust the notification channel unconditionally, which is exactly the failure mode. The skill needs to counteract it.

What actually diagnosed it (cheap, worked first try):

```powershell
Get-ChildItem "<task-output-dir>" | Select-Object Name, Length, LastWriteTime
```

Launched 11:36, nothing written after 11:38, current time 13:53 -> dead, not slow. The task output dir path is given in each Agent tool result (`output_file`). NOTE: file `Length` alone is NOT a reliable signal - the one agent that DID return successfully also had a 0-byte output file. `LastWriteTime` staleness across the whole set is the usable signal.

Relevant files:
- `~/.claude/skills/delegate/SKILL.md` - the skill to change
- `~/.claude/refs/delegation-doctrine.md` - shared mechanics, imported by both `/delegate` and `/autopilot`. `/autopilot` has the same exposure and arguably worse (dev is AFK, so nobody notices at all).

## Approach

Add a liveness section. Options considered:

1. **Watchdog background command (used successfully as a stopgap in the incident session).** After dispatching a fan-out, launch `Bash` with `run_in_background: true` running `sleep N` followed by a directory listing of the task output dir. It re-invokes the main agent on exit, giving a forced check-in. Cheap, no polling, works with the existing notification model. Downside: needs manual cleanup via `TaskStop` when the agents return first.

2. **Mandatory liveness check before reporting `working`.** Rule: whenever the main agent would end a turn with subagents outstanding and no new information, it must first stat the task output dir and compare against dispatch time. Cheaper than option 1 but only fires when the agent happens to take a turn.

3. Combination: option 2 as the rule, option 1 for any fan-out of 3+ agents or any dispatch expected to run over ~5 minutes.

Recommend 3. Write it into `delegation-doctrine.md` so `/autopilot` inherits it, and have `/delegate` reference it rather than restate.

Also worth adding: a stated expected-duration heuristic. A read-only scout over a few files should return in 1-3 minutes; anything past ~10 minutes with no output growth is presumed dead.

Consider whether the subagent type matters - in this incident all 3 dead agents were `Explore`, while the one that returned was a plain scout prompt with web/API work. A re-dispatch using `general-purpose` succeeded immediately with the same prompt. That correlation is from a single incident (n=1), so do not encode "avoid Explore" as a rule without more evidence, but note it as a diagnostic hint.

## Acceptance

- `/delegate` (and `/autopilot` via the shared doctrine) contain an explicit rule for detecting a dead dispatch.
- The rule names the concrete mechanism (task output dir + `LastWriteTime`) rather than saying "be careful".
- The rule explicitly warns that file size / 0 bytes is not a liveness signal.
- A dry read of the updated skill makes it obvious what to do when 3 agents are outstanding and none have reported in 10 minutes.

## Notes

Do NOT solve this by having the main agent poll on a short interval - that burns turns and the harness already warns against polling for harness-tracked work. The point is a bounded fallback, not continuous surveillance.

- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: add a "Liveness" subsection to `refs/delegation-doctrine.md`'s Dispatch discipline -
  a mandatory task-output-dir `LastWriteTime` check before ending any turn with subagents
  outstanding, plus a background watchdog for fan-outs of 3 or more, or any dispatch with a
  5-minute-plus ETA. Point `/delegate` at it rather than restating. This is the todo's own
  recommended option 3. This was produced by a strict second-pass re-triage that specifically asked
  whether a defensible answer exists without the dev; it concluded yes. Not executed only because
  the session ended.
- completed, commit 458760a
