<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1005 (done) took the message-fix option and explicitly left this detection option; 1029/1070 are marker pruning, 1065 is flutter-bump -->
# push-read-gate should also count a shell read of auto-commit.md

**Type:** task
**Origin:** ai

## Goal

A session that read `snippets/auto-commit.md` with `cat`/`Get-Content` is not blocked at push as if it
never read it.

## Context

Todo 1005 (done, 66f578b) took the message-fix option: `hooks/push-read-gate.py`'s deny message now
says only a Read-tool read counts. The detection option was left because it needs the PostToolUse
matcher in settings.json widened from `Read` to `Read|Bash|PowerShell` so the hook ever sees a shell
command; the builder had no access to settings.json. Without it, a correct read via the shell still
produces a block plus a forced re-read.

## Approach

1. Widen the PostToolUse matcher for push-read-gate.py in settings.json.
2. In the hook's PostToolUse arm, record a read when a Bash/PowerShell command reads
   `snippets/auto-commit.md` (cat, head, sed -n, Get-Content), matching on the path token.
3. Tests for each read form, plus a negative case (a command that only mentions the path).

## Acceptance

- A shell read of the snippet satisfies the gate; a mention without a read does not.
- The deny message is updated to match.
