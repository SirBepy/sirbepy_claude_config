<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped .claude/todos/ and done/ for shell-content-write-guard / heredoc / redirect: no hit. -->
# shell-content-write-guard reads a `>` inside quoted content as a redirect

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `hooks/shell-content-write-guard.py` from blocking a Bash call whose `>` is inside a
heredoc body or a quoted string, and decide whether the same hook should also see file writes
performed by an inline interpreter.

## Context

Hit live on 2026-08-26 in the `claude_usage_in_taskbar` repo. The blocked command was a
`python - <<'PY' ... PY` heredoc that patched a Playwright spec. Its body contained the literal
HTML string:

```
expect(payload["text/html"]).toContain("<strong>auth migration</strong>");
```

The hook rejected the whole call with:

> [shell-content-write-guard] `>` redirect writes file content to `auth` through the shell.

There is no redirect. It matched `>auth` inside `<strong>auth`, inside a single-quoted heredoc,
inside a string literal. The guard is scanning the raw command text without tracking quoting or
heredoc bodies, so any command carrying HTML, a Rust generic (`Vec<T> foo`), a shell example, or
a diff fragment can trip it.

The fix cost was small this time (fell back to the `Edit` tool) but the failure mode is bad: the
hook is a hard block, the message asserts something factually untrue about the command, and the
natural next move is to fight the message rather than the real constraint.

**Second, separate observation from the same session, lower confidence:** the guard exists to stop
file CONTENT being written through the shell (global `CLAUDE.md`, Shell Commands). It matches
`Set-Content`/`Out-File`/`>`/`>>`. It does NOT match
`python - <<'PY' ... io.open(p,"w",encoding="utf-8").write(s) ... PY`, which was used repeatedly
in that same session to rewrite source files and is arguably the exact thing the rule bans. Worth
a decision either way rather than leaving it implicit - the interpreter path may well be fine,
since it controls its own encoding and therefore avoids the BOM problem the rule was written for.

## Approach

1. Read `hooks/shell-content-write-guard.py` and find how it scans for `>`.
2. Strip heredoc bodies (`<<'X' ... X`, `<<X ... X`, `<<-X`) and quoted spans before matching, or
   at minimum require the `>` to be preceded by whitespace or a command terminator and followed by
   whitespace-then-a-path-like token. `<strong>auth` fails that shape; `foo > out.txt` passes it.
3. Add a `hooks/test_shell_content_write_guard.py` case per direction:
   - ALLOW: a heredoc body containing `</strong>`, `Vec<String>`, and `a > b` inside quotes.
   - ALLOW: a heredoc body containing the literal text `echo hi > file.txt` (documentation, not
     execution).
   - BLOCK: a real `echo "x" > file.txt`, and a real `... | Out-File foo`.
4. Settle the interpreter question separately, and write the answer into global `CLAUDE.md`'s
   Shell Commands section rather than only into the hook - the rule is what the model reads.

## Acceptance

- The exact 2026-08-26 command shape (heredoc containing `<strong>auth migration</strong>`) passes
  the hook.
- A genuine `>` redirect writing file content is still blocked.
- `python ci/run_all.py` green, including the new test cases.

## Notes

- Filed from a project session per global `CLAUDE.md`: spotting and filing global findings is
  allowed, editing the global tree from a project session is not. Do not fix this from
  `claude_usage_in_taskbar`.
- Duplicate of 476 - merged during /cleanup-todos 2026-08-29. Same defect in hooks/shell-content-write-guard.py: it scans the raw command string with no quote or heredoc awareness. This file's 2026-08-26 quoted-content instance (<strong>auth migration</strong>), its open inline-interpreter question, and two acceptance bullets were folded into 476 first.
