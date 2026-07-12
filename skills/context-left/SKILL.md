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

The script:
1. Reads `$CLAUDE_CODE_SESSION_ID` (set in every Claude Code shell) to identify this exact session.
2. PRIMARY: queries the daemon's authoritative endpoint `http://127.0.0.1:27182/context?session_id=<id>` - the single source of truth shared with the app's context chip, so the number matches the app and the window math is fixed in one place.
3. FALLBACK (daemon unreachable, e.g. app not running or an old binary): self-computes from this session's own transcript (`~/.claude/projects/<dir>/<session_id>.jsonl`):
   - occupancy = `input_tokens + cache_read_input_tokens + cache_creation_input_tokens` (latest turn)
   - remaining = `context_window - occupancy`, with the same sticky "any turn over 200K proves a >=1M window" correction the daemon uses.

## Output

One line, e.g.:

```
context left: 762K / 1M (76%)  [########--]  opus-4-8
```

Surface that line to the user as-is. If a `note:` line is present it means the exact context window could not be proven (the model name does not pin 200K vs 1M), so the number is a best estimate using the same assumption the app's UI makes, with one provable correction: if occupancy already exceeds 200K the window must be at least 1M. If a `warning:` line appears, the script could not match this session's transcript - either `CLAUDE_CODE_SESSION_ID` was unset, or it was set but no matching transcript existed (the warning says which) - and it fell back to the newest transcript, which may belong to a different session. Mention that caveat.

## Scope

The daemon endpoint is the single source of truth (fix the math in one place, consumed by the app chip, this skill, and autopilot self-regulation). The self-compute fallback keeps the skill working for any claude instance even when the daemon is down. On the go: when you ask this on your phone via remote control, the agent runs the skill PC-side and the answer comes back through the chat the phone already sees.
