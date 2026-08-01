---
name: context-left
description: Use when the user asks how much context is left or remaining, how full the context window is, how much room is left before it fills, or invokes /context-left. Reports remaining context-window tokens + percent for this session. Read-only, localhost-only.
---

# /context-left

> How much context window does THIS session have left?

Run the bundled Node script and report its output to the user. Node is always present (Claude Code runs on it).

```
node ~/.claude/skills/context-left/context-left.mjs
```

See the script's header comment for how it resolves the session and computes the window (daemon primary, transcript self-compute fallback).

## Output

One line, e.g.:

```
context left: 762K / 1M (76%)  [########--]  opus-4-8
```

Surface that line to the user as-is. If a `note:` line is present it means the exact context window could not be proven (the model name does not pin 200K vs 1M), so the number is a best estimate using the same assumption the app's UI makes, with one provable correction: if occupancy already exceeds 200K the window must be at least 1M. If a `warning:` line appears, the script could not match this session's transcript - either `CLAUDE_CODE_SESSION_ID` was unset, or it was set but no matching transcript existed (the warning says which) - and it fell back to the newest transcript, which may belong to a different session. Mention that caveat.

## Scope

The daemon endpoint is the single source of truth (fix the math in one place, consumed by the app chip, this skill, and autopilot self-regulation). The self-compute fallback keeps the skill working for any claude instance even when the daemon is down. On the go: when you ask this on your phone via remote control, the agent runs the skill PC-side and the answer comes back through the chat the phone already sees.
