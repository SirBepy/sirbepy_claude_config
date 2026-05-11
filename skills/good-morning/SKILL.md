---
name: good-morning
description: Triggers on /good-morning only. Morning routine dispatcher. Reads overnight handoff (`.for_bepy/TOMORROWS_AI_PROMPT.md`), surfaces ai_todos, then runs /clockify-reconciliator zirtue yesterday.
---

# /good-morning

> Morning routine. Reads overnight handoff from `/night-run`, surfaces flagged AI todos, then reconciles yesterday's Zirtue Clockify.

## Steps

### 1. Pull latest

```
git pull
```

If not in a git repo, skip this step silently.

### 2. Read overnight messages from agents

Check `.for_bepy/AI_MESSAGES_TO_TOMORROWS_AI.md`.

- If file exists: Read it. Surface its content to Joe verbatim (caveman-mode-friendly summary if very long, but never drop a section). These are notes from overnight tick agents about failures, surprises, or non-obvious tradeoffs that aren't visible in git history.
- After Joe acknowledges (a single "ok" / "yep" / "got it" is enough), delete the file:
  - `git rm .for_bepy/AI_MESSAGES_TO_TOMORROWS_AI.md`
- Defer the commit until step 5 batches all morning cleanup commits.

If the file doesn't exist, skip silently. No "no messages" output.

### 3. Read overnight prompt and execute it

Check `.for_bepy/TOMORROWS_AI_PROMPT.md`.

- If file exists: Read it. The file is a structured prompt the night-run finisher generated for this morning. It has these sections: Context, Verify checklist, Open decisions for Joe, Files changed, Failed plans, Suggested next steps.
- Surface the **Context** section as plain text, then ask via AskUserQuestion: "Run verify checklist?" with options: "Run all items", "Pick specific items", "Skip checklist".
  - **Run all:** execute each checklist item in order, one Bash/tool call each.
  - **Pick specific items:** follow up with a second AskUserQuestion (`multiSelect: true`) listing each checklist item as an option. Execute only selected items.
  - **Skip:** proceed to open decisions.
- The checklist items are concrete commands or inspections. Execute them; don't just print them.
- After the verify pass, surface **Open decisions for Joe** and **Suggested next steps** as one combined AskUserQuestion so Joe can pick what to work on (or defer all).
- Delete the file when done:
  - `git rm .for_bepy/TOMORROWS_AI_PROMPT.md`
- Defer the commit until step 5.

If the file doesn't exist, skip silently. No "no prompt" output.

### 4. Surface available AI todos

List `.for_bepy/ai_todos/*.md`. For each file, read its first heading + the priority/severity tag if present.

- If empty: skip silently.
- If non-empty: present the list to Joe via AskUserQuestion (or numbered chat if more than 4 items - then AskUserQuestion with "Pick one / Skip all / Show details for one"). Joe either picks one to work on now, picks "all" (loops through), or skips.
- Picking a todo hands off to the relevant skill or just opens the file inline. Do not auto-execute - Joe drives.

### 5. Commit morning cleanup

If steps 2 or 3 deleted any file, commit now via `/commit`:

```
/commit
```

Let `/commit` write the message. Do not bypass it.

If nothing was deleted, skip this step.

## Notes

- Steps 2, 3, 4 each handle "file missing" with silent skip - no "nothing to report" noise. Joe sees output only when there's something to act on.
- Step 5 batches deletions into a single `/commit` so the morning cleanup is one atomic commit.
- More morning tasks will be added here over time (ticket pickup, PR review, etc). Keep this skill as the single entry point.
- When adding new steps, list them here in order and make each step one clear action.
