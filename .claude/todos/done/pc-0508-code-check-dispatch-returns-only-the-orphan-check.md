<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Searched this backlog for "orphan", "preamble", "dispatch", "code-check", "return value".
     Nothing covers a dispatch whose findings are displaced by the orphan-check paragraph. -->
# A code-check dispatch can return only its orphan check, silently dropping every finding

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop a builder/reviewer dispatch from returning its process-hygiene proof INSTEAD of its actual
work product.

## What happened

2026-08-24, `claude_usage_in_taskbar`. A `/code-check` dispatch over a 30-file range completed
normally and its entire final message was the orphan check: *"No cargo/playwright processes exist.
The node/vite/playwright processes visible in the earlier broader scan... predate this dispatch."*
Zero findings, no summary line, no "no findings" statement either.

The analysis had actually run. On being asked to re-send findings only (without redoing the work) it
produced two properly-formatted findings, the Step 5 summary line, a dropped-finding log entry, and
verdicts on both specific questions it had been asked. **None of that was lost, it just never got
emitted the first time.**

## Why it is a real defect, not a one-off

The canonical builder preamble (`~/.claude/refs/builder-preamble.md`) places two instructions near
each other at the END of the prompt:

1. the orphan-check paragraph, which demands *"paste the actual command output proving it's gone"*
2. *"Your final message is your entire return value."*

Read together at emit time, the last concrete "paste this" instruction wins and becomes the final
message. The longer and more structured the real deliverable is (JSON blocks, a summary line, a
separate observations section), the more likely it is to be displaced.

**The dangerous part is that it is indistinguishable from a clean review.** A dispatch that returns
only an orphan check looks like "nothing found" to a caller who is not paying attention. Here it was
caught only because a zero-finding result on a 30-file range looked implausible. On a small diff it
would have passed as genuine.

## Approach

Options, roughly in order of preference:

1. **Move the orphan check out of the final message.** Require it earlier, or as a separate labelled
   block that explicitly is NOT the return value. The preamble already distinguishes the two ideas;
   it just does not order them.
2. **Make the return contract the LAST thing in the prompt**, after the orphan check, so
   "your final message is your entire return value" is what the model reads last.
3. **Have `/code-check` require an explicit summary line** (`code-check: N findings ...`) and treat
   its absence as a failed dispatch worth re-requesting, rather than as zero findings. Cheapest
   detection, does not fix the cause.

1 or 2 fix the cause; 3 is a backstop that would have caught this immediately. They compose.

Note the re-request worked perfectly and cost almost nothing, so the recovery path is sound - the
problem is purely that a caller has to notice.

## Acceptance

- A reviewer/builder dispatch that runs an orphan check still returns its findings as the final
  message, verified on a real multi-file review, not a toy prompt.
- A dispatch that genuinely finds nothing says so explicitly rather than emitting only hygiene
  output, so "no findings" and "findings lost" are distinguishable.

## Notes

- Dropped via /cleanup-todos 2026-08-29: already fixed. refs/builder-preamble.md now places the orphan-check and prefilter paragraphs BEFORE the 'Your final message is your entire return value' closer (commits 2cefa3d 2026-08-22 and b74996c 2026-08-26), which is option 2 from this todo's own Approach.
