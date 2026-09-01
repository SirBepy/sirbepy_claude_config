<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=8, reconfirm-count=1, content-hash=d6fec62f -->
<!-- duplicate-checked -->
# The shell-write guard blocks a `>` that is a comparison operator inside a heredoc body

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `hooks/shell-content-write-guard.py` reading a greater-than operator inside heredoc'd program
source as a shell redirect, without weakening the redirect detection it exists for.

## Context

Hit 2026-08-22. The blocked command was a python heredoc:

```
python - <<'PY'
h['runs'] = [r for r in h['runs'] if r['summary']['total'] > 0]
...
PY
```

The hook reported:

> `>` redirect writes file content to `0]` through the shell. Use the Write tool instead.

There is no redirect in that command. The `>` is a comparison operator inside a quoted heredoc body,
which the shell passes to python's stdin verbatim and never interprets. The captured "target" being
`0]` is the same token-split tell that todo 257 documented.

This is the **third** distinct false-positive class on this guard, and the first two are already
fixed and archived, so the pattern is the guard's scanning scope rather than any single regex:

- **257** (`done/`) - `2>/dev/null`, a file-descriptor redirect read as a content write.
- **289** (`done/`) - a command that merely NAMES a write cmdlet.
- this one - a `>` inside a heredoc body, i.e. text that is not shell at all.

**Second instance of this same class, 2026-08-22, and it matters more than the first because it
fires on a standard workflow rather than an ad-hoc script.** A `git commit -F-` heredoc was blocked
by the trailing `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` line, which every commit
message written per `CLAUDE.md` ends with. The guard reported:

> `>` redirect writes file content to `EOF` through the shell.

The captured target being the heredoc's own closing tag is the same token-split tell. Effect: the
heredoc route to `git commit -F-` is unusable for any conforming commit message, so the session fell
back to writing the message to a temp file with the `Write` tool and passing `-F <path>`. That
workaround is fine, but nobody should have to discover it three commits into a phase. Fixing the
heredoc-body scope (step 2 below) fixes this case too - no separate work.

**Third instance, 2026-08-27, zng-app.** A `python - <<'PY' ... PY` heredoc rewriting a Dart widget
was blocked by Dart arrow syntax in the body, `onTap: () => onChanged(true)`:

> `>` redirect writes file content to `onChanged` through the shell.

New detail this instance adds: the `>` here is the second character of a two-character operator
`=>`, so it is not a stray angle bracket in prose like the earlier cases - it is a token that can
never be a redirect no matter where it appears, heredoc or not. That gives a cheap partial fix
independent of the heredoc-scope work: a `>` immediately preceded by `=`, `-`, `!` or `<` is an
operator (`=>`, `->`, `!>`, `<>`), never a redirect. Worth doing as its own guard clause because it
also protects plain (non-heredoc) commands carrying arrow syntax.

Relevance is high and recurring rather than incidental: `=>` is standard Dart for expression-bodied
members, so every Dart repo (zng-app, zng-admin, zng-biller) trips this on any scripted source edit.

**Fourth instance, 2026-08-26, `claude_usage_in_taskbar`** (merged from todo 790 during
/cleanup-todos 2026-08-29). A `python - <<'PY' ... PY` heredoc patching a Playwright spec was
blocked because its body contained the literal HTML string
`expect(payload["text/html"]).toContain("<strong>auth migration</strong>");`:

> `>` redirect writes file content to `auth` through the shell.

The match was `>auth` inside `<strong>auth`, inside a string literal, inside a single-quoted
heredoc. What this instance adds beyond the heredoc scope: the guard tracks neither quoting nor
heredoc bodies, so ANY command carrying HTML, a Rust generic (`Vec<T> foo`), a shell example, or a
diff fragment can trip it. A step-2a operator exclusion does not cover this class; only real
quote/heredoc awareness does.

The guard's job is load-bearing and must stay: PowerShell 5.1 prepends a UTF-8 BOM on shell writes
and that has caused at least two real incidents. This is about scope, not about relaxing it.

**Open sub-question, merged from 790, lower confidence.** The guard exists to stop file CONTENT
being written through the shell. It matches `Set-Content`/`Out-File`/`>`/`>>`, but it does NOT
match `python - <<'PY' ... io.open(p,"w",encoding="utf-8").write(s) ... PY`, which is arguably the
exact thing the rule bans and was used repeatedly to rewrite source files in that same session.
Settle it either way rather than leaving it implicit: the interpreter path may well be fine, since
it controls its own encoding and so avoids the BOM problem the rule was written for. Write the
answer into global `CLAUDE.md`'s Shell Commands section, not only into the hook, since the rule is
what the model reads.

## Approach

1. Read `hooks/shell-content-write-guard.py` and find where it scans the command string. It almost
   certainly scans the whole string, heredoc bodies included.
2. Strip heredoc bodies before scanning: from `<<'TAG'` or `<<TAG` (or `<<-`) through the closing
   `TAG` line. A quoted-tag heredoc is never shell-interpreted, so nothing inside it can be a
   redirect and the whole body is safely out of scope.
2a. Independent of step 2, and cheaper: exclude a `>` immediately preceded by `=`, `-`, `!` or `<`,
   AND a `>` immediately followed by `=`. Those are the operators `=>`, `->`, `!>`, `<>`, `>=`,
   never redirects. The trailing-`=` half matters on its own: a preceded-by-only list still lets
   `byId >= 0` through, which is the 2026-08-31 instance below. Fixes the Dart-arrow case
   everywhere, including outside heredocs, and is a few lines if step 2 stalls on scoping.
3. Measure before wiring, per the hook doctrine in `.claude/todos/PLAN.md`, and note that a corpus
   measurement only proves no PAST command tripped it: hand-probe the built thing too. Todo 466's
   durable harness is the intended tool, and `C:\tmp\p2-corpus\commands.jsonl` (62,270 real
   commands) is the corpus if it still exists.
4. Add a case to `hooks/test_shell_content_write_guard.py` for each of the three classes, so the
   next one is a regression rather than a rediscovery.

## Acceptance

- The exact heredoc above passes the guard.
- A heredoc body containing `onTap: () => onChanged(true)` passes (2026-08-27 Dart-arrow case).
- A heredoc body containing `<strong>auth migration</strong>` and `Vec<String>` passes
  (2026-08-26 quoted-content case, from 790).
- A heredoc body containing the literal documentation text `echo hi > file.txt` passes (from 790).
- A heredoc body containing `const i = byId >= 0 ? byId : -1` passes, and one containing a
  triple-backtick fence passes (2026-08-31, claude_usage_in_taskbar, fifth instance - two
  rejections in one session on scripted TS/markdown edits; `>=` is the case step 2a's
  preceded-by-only list misses).
- `2>/dev/null` and a cmdlet-naming command still pass (257 and 289 stay fixed).
- A real content write (`echo x > f.txt`, `Set-Content`, `Out-File`, `>>`) is still blocked, proven
  by test cases, not by inspection.
- `python ci/run_all.py` exits 0.

## Notes

Workaround while this is open: write the script to a scratch file with the Write tool and run it by
path. That is what unblocked the 2026-08-22 case.
