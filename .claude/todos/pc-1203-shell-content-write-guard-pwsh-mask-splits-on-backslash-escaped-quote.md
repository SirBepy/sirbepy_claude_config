<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped .claude/todos/ and done/ for shell-content-write-guard, backslash escape, nested quote,
     DQUOTE_RE_PWSH: no prior hit covers this exact mechanism (checked 476, 790, 257, 289, 956, 908,
     845, which cover heredoc bodies, arrow operators, cmdlet names, and fd redirects - a different
     class each). -->
# shell-content-write-guard's PowerShell quote-mask splits on a bash-style backslash-escaped quote

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `hooks/shell-content-write-guard.py` from false-positive-blocking a Bash-tool command whose
double-quoted argument contains a bash-style backslash-escaped inner quote (`\"..\"`), when that
escaped span itself contains an unmasked `>`.

## Context

Hit live 2026-10-20 in `claude_usage_in_taskbar`, committing via `commit-pathspec.sh -m "..."`. The
`-m` value (passed through the Bash tool, which the tool's own description states runs "Git Bash
(POSIX sh), not cmd.exe or PowerShell") contained:

```
...the literal text \"</body>\" got its script truncated...
```

The hook rejected the call with:

> [shell-content-write-guard] `>` redirect writes file content to `\QSTR` through the shell.

Root cause, traced by reading `hooks/shell-content-write-guard.py:93-104,206-219,243-254,257-277`
this session (receipt, not a guess):

- `find_violation` masks the command TWICE, once under `DQUOTE_RE_BASH = "(?:[^"\\]|\\.)*"` and once
  under `DQUOTE_RE_PWSH = "(?:`.|""|[^"])*"`, and blocks if EITHER masked pass flags a redirect
  (deliberate fail-closed design per the module docstring, "blocks if either flags a hit").
- Under bash rules, `\"` is a valid escaped quote, so `\\.` consumes it as one unit and the whole
  `-m` argument masks as a single `QSTR` span - this pass is clean.
- PowerShell has NO backslash-escape for `"` (it uses backtick or doubled `""`), so under
  `DQUOTE_RE_PWSH` a lone `"` preceded by `\` is just an ordinary `[^"]` char followed by a REAL
  closing quote. The first `\"` in the message therefore closes the outer quoted span early (right
  after swallowing the preceding backslash as ordinary content), and the second `\"` a few chars
  later opens a NEW quoted span. The text between those two escaped-quote markers - here, literally
  `</body>` plus the second escaped quote's leading backslash - is left UNMASKED under the pwsh pass.
- `REDIRECT_RE` then matches the unmasked `>` in `</body>` (preceded by `y`, not excluded; followed
  by `\`, not `=`), and `(\S*)` greedily captures the next non-whitespace run, which is the backslash
  plus the following masked span's literal placeholder text - producing the exact observed target
  `\QSTR`. This is a mechanical, fully reproducible derivation of that string, not a coincidence.

This is a distinct false-positive class from the ones already fixed:

- **476/790** (`done/`) - heredoc bodies and quoted HTML/Dart-arrow content with no backslash
  escaping involved; fixed by heredoc-body stripping and arrow-operator exclusion.
- **257/289** (`done/`) - fd-redirect and bare-cmdlet-name false positives, unrelated mechanism.
- **this one** - a BASH-valid backslash-escaped quote *inside* an otherwise normal (non-heredoc)
  double-quoted argument, misread as a real quote boundary under the guard's own PowerShell-dialect
  masking pass. The dual-dialect design is sound in general (catches real cross-dialect ambiguity)
  but has no allowance for `\"` specifically meaning "escaped quote, not a boundary" when the
  command demonstrably originates from the Bash tool (POSIX sh), not PowerShell.

## Approach

1. Confirm the Bash tool always tags its `cwd`/payload in a way the hook can distinguish "this
   command runs under Git Bash" from "this command runs under PowerShell" (the harness presumably
   already knows which tool invoked it - check `read_payload`'s fields in `_hooklib.py`). If the
   hook can identify the originating tool, skip the PowerShell-dialect mask entirely for a Bash-tool
   call (and skip the bash-dialect mask for a PowerShell-tool call) instead of always running both
   and OR-ing the hits - the dual-mask approach exists to hedge against not knowing the dialect, but
   if the payload already states it, use that instead of guessing defensively in both directions.
2. If the tool identity isn't available to the hook, a narrower fix: before running
   `DQUOTE_RE_PWSH`, pre-mask (or skip) any `\"` sequence that bash-rules already consumed as part of
   a valid escaped-quote span - i.e. derive the pwsh mask from the ALREADY-bash-masked text's quoted
   spans rather than re-scanning the raw command from scratch under pwsh rules, so a span the bash
   pass proved was one contiguous quoted string can't be re-split by the pwsh pass finding a bare
   `"` that bash already explained away as an escape.
3. Add a case to `hooks/test_shell_content_write_guard.py`: a `-m "... \"</body>\" ..."`-shaped
   argument (or any backslash-escaped-quote span containing a bare `>`) passes the guard when issued
   as a Bash-tool command.
4. Re-verify a genuine PowerShell call whose doubled-quote escaping (`""..""`) hides a real
   redirect target is still caught - this fix must not weaken the PowerShell-dialect pass for actual
   PowerShell commands, only stop it from misreading bash's own escape convention.

## Acceptance

- The exact 2026-10-20 command shape (`-m "... \"</body>\" ..."` via the Bash tool) passes the
  guard.
- A real PowerShell redirect using `""`-doubled-quote escaping to hide a write target is still
  blocked.
- `python ci/run_all.py` (or the project's equivalent hook test runner) green, including the new
  case.

<!-- loop-skip: dev deferred 2026-10-24 -->
## Deferred questions

Written by /auto-do-todos on 2026-10-23. Deferred by /loop-todos on 2026-10-24: Jarvis (answering for Joe while he was asleep) picked "you decide"; Claude's 2026-10-24 re-check of the real write target found the fix needs a `hooks/` or `settings.json` write, which prompts for permission, so it waits for an attended session.

- [ ] [TOOLING] Run this todo in an attended session (say which). Its fix writes to `hooks/` or `settings.json`, which `hooks/sensitive-file-guard.py` gates with a permission ask, and the autopilot rules bar a dispatched subagent from those writes, so an unattended loop cannot land it.

## Notes

- Filed from a project session per global `CLAUDE.md`: spotting and filing a global-tree finding is
  allowed from a project session, editing `~/.claude` itself is not. Do not fix this from
  `claude_usage_in_taskbar`.
- Workaround used this session: reworded the commit message to avoid literal `</body>`-shaped text
  entirely (described it in prose instead of quoting the tag). That is a viable fallback any future
  session can reuse without waiting on this fix, but it costs a retry each time it's rediscovered.
