---
name: sleep-when-done
description: Triggers on /sleep-when-done only. Tells Claude to finish the current task without interruption, auto-answering any questions by picking the best option, then putting the PC to sleep.
---

# /sleep-when-done

> the dev is leaving. Finish the task, don't ask questions, then sleep the PC.

**Trigger:** `/sleep-when-done` only. Never auto-invoke.

## Behavior contract

When the dev runs this command, you commit to the following until the task is fully complete:

1. **No questions to the dev.** the dev is gone. If a question arises (clarification, ambiguity, multiple valid options), pick the option you judge best given context and proceed. No log - the dev doesn't read a running decision log; git history + your final summary are the record.
2. **Genuine blocker** (not just a judgment call - credentials, destructive op, hardware, or anything else you truly cannot proceed past): write one file to `.for_bepy/autopilot-logs/<slug>.md` (create the folder if missing) with what happened, why blocked, and what's needed from the dev. Then stop that piece of work and continue anything unblocked.

```
# <topic>

What happened: <what you were doing>
Why blocked: <credential / destructive-op / hardware / other, one line>
Needs from you: <the specific physical action required>
```

3. **Run normal workflows** otherwise: invoke skills, follow CLAUDE.md rules, commit + push as usual.
4. **At the very end**, after all work + commits + pushes are done, put the PC to sleep.

## Sleep command

Detect platform from the environment (already in your system prompt).

**Windows** (`win32`):
```
rundll32.exe powrprof.dll,SetSuspendState 0,1,0
```
Note: if hibernation is enabled, this hibernates instead of sleeps. That's fine - same end result for the dev.

**macOS** (`darwin`):
```
pmset sleepnow
```

**Linux** (`linux`): not supported. Write a file to `.for_bepy/autopilot-logs/<slug>.md` noting sleep was skipped (unknown platform) - there's no chat message after this step to convey it otherwise.

Run the command via Bash as the absolute last action. No text after it.

## Order of operations

1. Do the work the dev asked for.
2. Whenever stuck on a decision, pick and proceed. If genuinely blocked, log to `.for_bepy/autopilot-logs/`.
3. Commit + push per project rules.
4. Final Bash call: sleep command for the detected platform.
