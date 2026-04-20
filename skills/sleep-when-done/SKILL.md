---
name: sleep-when-done
description: Triggers on /sleep-when-done only. Tells Claude to finish the current task without interruption, auto-answering any questions by picking the best option and logging them to COMMENTS_FOR_BEPY.md, then putting the PC to sleep.
---

# /sleep-when-done

> the dev is leaving. Finish the task, don't ask questions, then sleep the PC.

**Trigger:** `/sleep-when-done` only. Never auto-invoke.

## Behavior contract

When the dev runs this command, you commit to the following until the task is fully complete:

1. **No questions to the dev.** the dev is gone. If a question arises (clarification, ambiguity, multiple valid options), pick the option you judge best given context, proceed, and log it.
2. **Log every auto-decision** to `COMMENTS_FOR_BEPY.md` in the project root (cwd). One entry per decision.
3. **Run normal workflows** otherwise: invoke skills, follow CLAUDE.md rules, commit + push as usual.
4. **At the very end**, after all work + commits + pushes are done, put the PC to sleep.

## Logging format

Append to `COMMENTS_FOR_BEPY.md` (create if missing). One block per decision:

```
## <YYYY-MM-DD HH:MM> - <short topic>
**Question:** <what you would have asked the dev>
**Options considered:** <brief list>
**Picked:** <choice>
**Reason:** <one line>
**Where:** <file/area affected, if any>
```

If file doesn't exist, create with a top-level `# Comments for Bepy` header, then the first block.

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

**Linux** (`linux`): not supported. Log to `COMMENTS_FOR_BEPY.md` that sleep was skipped (unknown platform).

Run the command via Bash as the absolute last action. No text after it.

## Order of operations

1. Do the work the dev asked for.
2. Whenever stuck on a decision, pick + log to `COMMENTS_FOR_BEPY.md`.
3. Commit + push per project rules.
4. Final Bash call: sleep command for the detected platform.
