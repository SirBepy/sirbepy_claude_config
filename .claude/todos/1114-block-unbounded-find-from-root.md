<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=HARD, worth=9, reconfirm-count=1, content-hash=64423f41 -->
# Hook-block unbounded `find /` and `grep -r /` from subagents

**Type:** skill-improvement
**Origin:** ai (mc_plugins_tag Dragon Balls session 412b, 2026-10-06)

## Goal
An unbounded filesystem scan from `/`, `C:/` or `$HOME` is refused mechanically, not only by prose.

## Context
`refs/builder-preamble.md` already says "Never run an unbounded `find` or `grep -r` from `/`, `C:/`,
or `$HOME`", and every dispatch in that session carried the line. Two sonnet subagents still ran
`find / -iname ConsoleCommandSenderMock*.class -o -iname mockbukkit*.jar` (PID 23360, started 12:26)
and `find / -ipath *phosphor* -iname *.css` (PID 59088, 12:34). Both kept scanning the whole drive for
more than an hour after their subagents finished. Joe only found out because he asked about a terminal
window, and killing them needed his explicit approval (the classifier blocked it first). The rule
exists, but nothing enforces it.

## Approach
Add a PreToolUse Bash/PowerShell hook (or extend an existing shell guard) that denies `find` with a
first path argument of `/`, `/c`, `C:/`, `C:\`, `~` or `$HOME`, plus `grep -r`/`rg` rooted the same
way, and tells the caller to scope to the repo or a cache dir. Add a self-test in `hooks/test_*.py`.

## Acceptance
- `find / -name x` is denied with a message naming the narrower alternative.
- `find ./src -name x` and `find C:/Users/tecno/.gradle/caches -name x` pass.
- `python ci/run_all.py` is green.
