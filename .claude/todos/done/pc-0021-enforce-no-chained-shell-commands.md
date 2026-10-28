<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=HARD, reconfirm-count=2, content-hash=9973bf22 -->
# Enforce the "never chain shell commands" rule with a hook instead of willpower

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop Claude from violating the global CLAUDE.md rule "Never chain commands with `&&`, `;`, or
`|`, one command per call" and the related "one command per call, always" phrasing, both
broken repeatedly across sessions (2026-07-15, 2026-07-17) with zero consequences, because
nothing enforces it.

## Context

The rule lives in `C:/Users/tecno/.claude-fibo/CLAUDE.md` (Shell Commands section) and is
restated in the /commit skill's Rules. Long sessions drift: the model reaches for `&&` under
time pressure, or bundles several statements onto separate lines in one call, and the harness
happily executes it either way. This is an enforcement gap, not a be-more-careful item, the
`/close` retrospective keeps surfacing it.

Two concrete incidents on record:
- 2026-07-15: multiple `cd X && npm Y` Bash calls, literal `&&` chaining.
- 2026-07-17 (`feature/test-shopping-cart-revamp` session): no literal `&&`/`;`/`|`, but
  several independent statements bundled via newlines into one call, e.g. a claim-file write
  pattern (`PID=$$` / `TS=$(date...)` / `printf ...` / `mv -n ...`, 4 statements, one call,
  repeated 3 times), a `git status --porcelain` + `echo` + `git diff` combo in one call, and
  PowerShell blocks chaining multiple `Invoke-RestMethod` calls. None of these individually
  broke anything, but they all violate the letter and spirit of "one command per call,
  always": the rule exists so a failure in an earlier statement doesn't silently get masked by
  a later one succeeding in the same call.

This is the same shape of problem as `.claude/todos/89-block-bash-backend-writes-hook.md` (a
`PreToolUse` hook enforcing a different shell-discipline rule), the same mechanism could work
here.

## Approach

Use the `update-config` skill's hook mechanism (see `~/.claude/hooks/` for existing examples,
e.g. `gh-account-switch.sh`): a global `PreToolUse` hook on the Bash/PowerShell tools that
inspects commands before they run:
- Reject (or warn-and-block) commands containing top-level `&&`, `;` (outside a quoted
  string literal), or `|` between commands, the letter of the rule.
- Also flag multi-line command blocks with more than one non-comment, non-continuation
  top-level statement, to catch the newline-separated case from the 2026-07-17 incident.
  Harder to do robust static detection for this without false-positiving on legitimate
  multi-line constructs (a `for`/`while` loop body, a heredoc); may need to scope this part
  more narrowly, e.g. only flag when 2+ lines each independently look like a complete
  top-level command, not a continuation of the previous one.
- Care needed to avoid false positives: `;` inside quoted args, `|` in legitimate single
  pipelines Joe allows (the rule as written bans them, so start strict and loosen if it
  annoys), heredoc bodies, and PowerShell `Where-Object { ... }` script blocks (PowerShell
  one-liners with pipes are idiomatic, decide with Joe whether the PowerShell tool is exempt;
  the original rule predates heavy PowerShell usage and may only have meant Bash).
- Exempt legitimate single-logical-operation constructs (a `for`/`while` loop body, a
  heredoc), the rule's intent is "don't chain independent commands," not "never write a
  loop."
- Prototype as warn-only first, review a week of hits, then flip to block. Alternative
  rejected: another CLAUDE.md restatement (already exists twice over, demonstrably
  insufficient).

## Acceptance

- A chained `cd x && npm y` Bash call gets rejected/warned by the hook with a message naming
  the rule.
- A test call like `echo a; echo b` (literal chaining) gets rejected/blocked with a clear
  message pointing at the rule.
- The newline-separated multi-statement case (e.g. 3+ independent commands in one call, no
  literal operators) is at least flagged, ideally blocked, without false-positiving on a
  genuine loop or heredoc.
- Normal single commands, quoted semicolons, and (if exempted) PowerShell pipelines pass
  untouched, verify with a live no-op test per
  [[verify-shared-mechanism-scope-empirically]] before considering this done.
- Hook lives in global settings via the update-config skill's format, documented where the
  rule is.

## Notes

MERGED 2026-07-27: folded in `123-enforce-one-shell-command-per-call.md` (a duplicate
proposal for the same hook), which is why this file's Context/Approach/Acceptance now cover
both the literal-operator case (this todo's original scope) and the newline-separated
multi-statement case (123's distinct contribution). Todo 123 was deleted as a duplicate;
nothing from it was lost.

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 119; renumbered to 21 per the max+1 id rule. Confirmed by dev 2026-08-07.
- Re-verified 2026-08-08: premise still holds.
- Duplicate of 07 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.

## Open questions

Written by /auto-do-todos on 2026-08-08. `/cleanup-todos` flagged this and todo 07 as a dedupe pair
with mutually exclusive resolutions: 07 wants the rule narrowed, this one wants it hook-enforced
literally. The dev declined to pick on paper and asked to test first.

- [ ] [TOOLING] This todo's warn-only prototype IS the experiment 07 now depends on, so build it
      first rather than treating the two as competing proposals. See 07's Open questions for the
      decision rule that reads this hook's hit log. Whichever way the log points, both todos close
      together, and only one of them ships a rule change.
