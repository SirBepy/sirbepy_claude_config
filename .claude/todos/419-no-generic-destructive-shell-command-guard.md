<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# No generic destructive-shell-command guard exists, only purpose-built ones

**Type:** task
**Origin:** ai

## Goal

One `PreToolUse` Bash guard covering the whole class of catastrophic commands, instead of relying on
the model remembering not to run them.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

Of 41 hooks here, every destructive-command guard is narrow and purpose-built: flutter workdir,
package manager pinning, commit and PR markers. **Nothing blocks the general class.** A bare
`rm -rf ~`, a `DELETE FROM` with no `WHERE`, a `curl | sh`, or a `git reset --hard` over another
agent's uncommitted work is currently prevented only by prose in CLAUDE.md plus the delegation
doctrine's ban list, which a subagent has already been observed to violate.

Two reference implementations, both real and readable:

**`poshan0126/dotclaude/hooks/block-dangerous-commands.sh`** - one PreToolUse Bash guard covering:
protected-branch push, bare push while on a protected branch, force-push (**allowing
`--force-with-lease`**), `rm -rf /` and `~` and `$HOME` and `../..`, system-directory deletes,
`DROP TABLE`, `DELETE FROM` without `WHERE` (parsed **per statement via awk**, not a naive line
regex), `chmod 777`, `curl | sh`, raw writes to `/dev/`, `mkfs`, `dd`, `git reset --hard`,
`git clean -f`, and unguarded package publish.

**`brain-bootstrap/.../hooks/terminal-safety-gate.sh`** - the better architecture. Same idea, but with
a `CLAUDE_HOOK_PROFILE=minimal|standard|strict` env dial choosing which severity tier is enforced.
Interactive editors, REPLs and bare `sleep N` are always blocked; SQL and `git reset` at standard;
pipe-to-shell, `eval` and `dd` at strict. Existing guards here have no shared severity concept, so
every guard is all-or-nothing.

Note the overlap to resolve rather than duplicate: `hooks/` already blocks bare package-manager
commands (todo 76, in `done/`) and there is prior history on shell chaining (todos 07 and 64, both
`done/`, both concluding the chaining rule was unworkable in PowerShell). Read those before writing
patterns, so this does not re-fight a settled argument.

## Approach

1. Read the two reference scripts in the harvest corpus. Take `terminal-safety-gate.sh`'s tiered
   profile structure and `block-dangerous-commands.sh`'s pattern coverage.
2. Read `done/07-no-chaining-rule-is-unworkable-in-powershell.md` and
   `done/64-no-shell-chaining-rule-has-no-enforcement.md` first. Whatever those concluded about
   PowerShell parsing constrains what is implementable here. This environment is PowerShell-primary
   with Bash available, so the guard must handle both syntaxes or explicitly scope itself.
3. Inventory what the existing 41 hooks already block, and write the guard to cover only the
   remainder. Two hooks blocking the same command with different messages is worse than one.
4. Implement with a severity dial. Default tier should be whatever blocks the genuinely
   unrecoverable operations without tripping on daily work; `git reset --hard` in particular is
   already banned for subagents on paths they do not own but is legitimate for the dev.
5. Do the `DELETE FROM`/`DROP TABLE` case properly, per-statement, or leave it out. A naive regex
   here produces false positives on any file containing SQL text, which trains everyone to ignore
   the guard.
6. Write fixture tests alongside it, matching the existing `hooks/test_*.py` convention. Include
   negative cases: `--force-with-lease` must pass, a `DELETE` with a `WHERE` must pass.

## Acceptance

- Every pattern in the guard has a passing test and a passing NEGATIVE test.
- `git push --force-with-lease` is allowed; bare `--force` to a protected branch is blocked.
- No command already blocked by an existing hook is blocked twice.
- The severity dial works: the same command is blocked at `strict` and allowed at `minimal`.
- Real test output pasted, not claimed.

## Notes

Resist making the default tier `strict`. A guard that fires on legitimate work gets disabled, and
then it protects nothing. Start at the tier that only catches the unrecoverable.
