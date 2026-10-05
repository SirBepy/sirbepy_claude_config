---
name: sleep-when-done
description: Triggers on /sleep-when-done only. Puts the PC to sleep as the final step once this session's fast checks have passed.
---

# /sleep-when-done

> the dev is leaving. Once the work is done and verified, sleep the PC.

**Trigger:** `/sleep-when-done` only. Never auto-invoke.

Stays model-invocable (no `disable-model-invocation`) on purpose: `/autopilot --sleep` and
`/close /sleep-when-done` both chain-invoke it via the Skill tool, and flagging it would silently
break those two paths (todo 842). The "Never auto-invoke" rule above, not the frontmatter, is what
stops Claude firing this unprompted.

**Precondition:** never sleep on red - the project's fast checks (typecheck, unit tests, lint, build, whichever the project has) must have passed this session before the sleep call runs.

## Sleep command

**Windows** (`win32`), via PowerShell:
```
rundll32.exe powrprof.dll,SetSuspendState 0,1,0
```
Note: if hibernation is enabled, this hibernates instead of sleeps. That's fine - same end result for the dev.

Run the command via PowerShell as the absolute last action. No text after it.

For the unattended-work contract (auto-answering, blocker logging, verification), this runs under `/autopilot` - see autopilot's `--sleep` flag.
