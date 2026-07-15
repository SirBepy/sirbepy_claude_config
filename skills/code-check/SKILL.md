---
name: code-check
description: Triggers on /code-check. Structural code review - file splits, DRY, dead code. Writes findings to the todos backlog. Callable standalone or from /close.
argument-hint: "[uncommitted|unpushed|<path>|<hash>]"
---

# /code-check

> Structural review: file splits, DRY, dead code. Writes findings to ai_todos.

## Scope resolution

Determine what to review based on args:

| Arg | What to run |
|-----|-------------|
| `uncommitted` | `git diff HEAD --name-only --diff-filter=ACM` |
| `unpushed` | `git log @{u}..HEAD --name-only --diff-filter=ACM --format=` |
| Looks like a file path | treat as single-file list |
| Looks like a hash or range (`abc1234`, `HEAD~3..HEAD`) | `git diff <arg> --name-only` |
| No args | ask using AskUserQuestion (see below) |

When asking, options:

- "Uncommitted changes" - files changed but not yet committed
- "Unpushed commits" - commits made since last push
- "Specific file or path" - follow up asking the dev to type the path (plain message, not AskUserQuestion)
- "Commit hash or range" - follow up asking the dev to type the hash or range

## Step 0 - Skill description budget

Before filtering, scan the resolved scope for any `SKILL.md` files. For each, read the `description:` frontmatter and count its words. If over budget (> ~25 words / 120 chars), record a finding - unless the extra length is a trigger keyword that can't be cut without breaking the skill's firing (same judgment as bepy-skill-creator's Description budget gate):

```json
{ "title": "[skill] description over budget", "files": ["path"], "problem": "description is N words; skill descriptions load into every session's system prompt, so verbosity is a per-session token cost", "fix": "trim to trigger surface (~25 words), preserving every trigger clause and when-to-use keyword" }
```

If scope has no `SKILL.md` files, skip this step.

## Filter to code files

After resolving, filter to code files only. Drop: `.md`, `.json`, `.toml`, `.yaml`, `.yml`, `.gitignore`, anything under `.for_bepy/`, `.claude/todos/`, or `memory/`.

If the filtered list is empty (and Step 0 produced no findings): print "No code files in scope." and stop.

## Step 1 - Size check

For each file in scope, get line count: `wc -l "path"` via Bash tool.

If > 400 lines AND has an obvious split seam (separate concerns, reusable unit, clear module boundary), record:

```json
{ "title": "[file] should be split", "files": ["path"], "problem": "[file] is N lines, mixes [X] and [Y]", "fix": "split at [boundary] into [new-file]" }
```

If no obvious seam, skip that file.

## Step 2 - DRY pass

For each new top-level symbol in scope (function, const, class, interface, type, export, def, func, local function - language-dependent): Grep the repo for equivalents by name, shape, and purpose. For each duplicate found, record:

```json
{ "title": "Duplicate: [symbol]", "files": ["path:line (new)", "path:line (existing)"], "problem": "what duplicates what (one sentence)", "fix": "delete X and import Y / extract shared util to Z" }
```

Cap: ~3 Grep calls per symbol. Use only Grep, Read, and Glob - no shell pipelines. If scope has zero new top-level symbols (body-only edits), skip this step.

## Step 3 - Dead code pass

For each new top-level symbol: `Grep pattern: "\\b<symbol>\\b", output_mode: "count"`. Count <= 1 (definition only) = never called. Also flag: unreachable branches, commented-out blocks left in, imports never read.

```json
{ "title": "Dead code: [symbol]", "files": ["path:line"], "problem": "one sentence", "fix": "delete / uncomment / wire up at X" }
```

## Step 4 - Output

Merge findings from Steps 0-3.

**If the project has a repo root for `.claude/todos/`:** write each finding as a `.md` file there, per `~/.claude/skills/close/ai-todos-format.md` (filename/id rules, git-policy self-heal; create the folder if missing). Format:

```markdown
<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# [title]

**Type:** task

## Goal
[what needs to happen]

## Context
[problem. Cite files as path:line.]

## Approach
[fix]

## Acceptance
[how to verify it is done]
```

**If not in a project (no repo root):** print all findings inline, one block per finding.

Print a summary line:

```
code-check: N findings (A size, B DRY, C dead code, D desc). M written to todos.
```

If zero findings: `code-check: No structural issues found.`
