---
name: pickup
description: Triggers on /pickup only. Reads the next-session handoff written by /next-ai-prompt, runs the verify checklist, then starts tackling suggested next steps.
---

# /pickup

> Resume from where the last session left off.

## Step 1 - Check for handoff

Read `.for_bepy/NEXT_AI_PROMPT.md` (use `git rev-parse --show-toplevel` if repo root is unclear).

If not found: output "No handoff found." and stop.

## Step 2 - Surface context

Print the **Context** section verbatim.

## Step 3 - Run verify checklist

File has a `## Verify checklist` section with `- [ ]` items. Execute each in order as real shell commands or inspections. Do not just print them.

## Step 4 - Surface open decisions and next steps

Combine **Open decisions** and **Suggested next steps** into one AskUserQuestion. Dev picks what to work on or defers all.

If 4 or fewer combined items: one option each. If more than 4: show top 4, list rest as plain text.

## Step 5 - Clean up and commit

```
git rm .for_bepy/NEXT_AI_PROMPT.md
```

Then run `/commit`.

## Notes

- Steps 2-4 skip silently if their sections are empty or say "None."
- Never commit the deletion until step 5. Never bypass `/commit`.
