---
name: work-recap
description: Triggers on /work-recap only. Dispatches to a named recap variant (e.g. zirtue weekly, zirtue daily). Each variant lives in a subfolder under this skill.
argument-hint: "zirtue [weekly|daily] [copy]"
---

# /work-recap

> Dispatch to a work-recap variant. Variant files live under this skill's folder.

## Step 1 - Parse args

Expected: `/work-recap <group> <variant> [copy]`

Examples:
- `/work-recap zirtue weekly`
- `/work-recap zirtue daily`
- `/work-recap zirtue daily copy`

If `<group>` or `<variant>` is missing, ask the dev which recap to run via AskUserQuestion. List the available variants from the table below.

The optional trailing `copy` flag tells the variant to also copy the final output file to the system clipboard after writing it.

## Step 2 - Resolve the variant file

Variant file lives at `~/.claude/skills/work-recap/<group>/<variant>.md`.

Available variants:

| Group | Variant | File |
|-------|---------|------|
| zirtue | weekly | zirtue/weekly.md |
| zirtue | daily | zirtue/daily.md |

If the file does not exist, list what exists and stop.

## Step 3 - Run the variant

Read the variant file in full, then follow its instructions exactly. The variant owns everything: window, data sources, output path, output format.

Pass the `copy` flag through to the variant (it decides how to honor it, typically by piping the final file to clipboard at the end).

## Rules

- Never run recap logic in this file. This file only dispatches.
- Never chain shell commands. One Bash call at a time.
- The variant file is the source of truth for its behavior.
