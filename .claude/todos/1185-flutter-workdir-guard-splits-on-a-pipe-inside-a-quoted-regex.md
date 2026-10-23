<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: todo 908 (done) fixed the same guard for a keyword inside a quoted string, but this one comes from the chain splitter, not the keyword match. -->
# flutter-workdir-guard splits on a pipe inside a quoted regex

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `hooks/flutter-workdir-guard.py` from denying a Bash command in which `flutter` is only a
word inside a quoted `grep -E` alternation.

## Context

On 2026-10-15, in a revaire-mobile session, this Bash call was denied with
"fvm/flutter/dart invoked as the leading command":

```
F="...\tasks\bbukdnt9g.output"; sed 's/\x1b\[[0-9;]*[A-Za-z]//g' "$F" | grep -a -n -E "FILE-|JUnit totals|❌ .*\(/flows|✅ .*\(/flows|flutter  " | cut -c1-200
```

No flutter, fvm or dart command runs there. `flutter` is the last alternative inside a
double-quoted ERE. The cause is `CHAIN_SPLIT_RE = re.compile(r"&&|\|\||;|\n|\|")`
(`hooks/flutter-workdir-guard.py:69`). It splits the raw command on every `|`, including the ones
inside quotes. The segment `flutter  " ` then tokenizes with `flutter` as its first token, and the
Bash leading-command branch (around line 155) denies it.

Todo 908 fixed the keyword-in-quotes form of this bug. The splitter itself still ignores quotes,
so any quoted regex alternation that contains `|flutter`, `|fvm` or `|dart` re-triggers the
denial. A working command had to be rewritten to get past it.

## Approach

1. Reproduce: feed the command above as a `PreToolUse` Bash payload and confirm it denies.
2. Split chains with a quote-aware splitter. Reuse whatever `_hooklib.py` already has after todo
   893's tokenizer extraction, rather than adding a third copy. If nothing there is quote-aware,
   add one shared helper and use it in both of this file's split sites (lines ~155 and ~166).
3. Check the other guards that use the same `CHAIN_SPLIT_RE` pattern for the same bug.

## Acceptance

- The command above is allowed.
- `flutter --version | head -3` run through the Bash tool is still denied.
- A regression test covers both cases in the guard's test suite.

## Open questions

Written by /auto-do-todos on 2026-10-23. The next run opens with these.

- [ ] [TOOLING] Run this todo in an attended session (say which). Its fix writes to `hooks/` or `settings.json`, which `hooks/sensitive-file-guard.py` gates with a permission ask, and the autopilot rules bar a dispatched subagent from those writes, so an unattended loop cannot land it.
