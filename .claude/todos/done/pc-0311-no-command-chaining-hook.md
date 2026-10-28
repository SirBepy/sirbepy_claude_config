<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Hook: block chained shell commands (`&&`, `;`, `|`) in Bash/PowerShell calls

**Type:** skill-improvement
**Origin:** ai

## Goal
Make the global "one command per call" rule self-enforcing, the same way the em-dash and bare-question rules got hooks (`307-em-dash-stop-hook.md`, `308-bare-question-stop-hook.md`).

## Context
`~/.claude-personal/CLAUDE.md` > Shell Commands states: "Never chain commands with `&&`, `;`, or `|` - one command per call, always, git included."

It was violated repeatedly across a 2026-08-06 session and never caught, e.g.:
- `cd "C:/..." && git add test/features/team/slow_team_service.dart`
- `cd "C:/..." && sed -i '...' file && grep -n ... file`
- PowerShell: `dart run build_runner build 2>&1 | Select-Object -Last 2; flutter analyze 2>&1 | ...`

The rule is a prose instruction with no enforcement, so compliance decays over a long session exactly when call volume is highest. Note the rule as written also forbids `|`, which collides with idiomatic PowerShell (`| Select-Object -Last 20`) and with the pipelines the `/commit` skill's own comment-noise prefilter requires - so a naive block would fire constantly on legitimate calls.

## Approach
1. Add a `PreToolUse` hook matching the `Bash` and `PowerShell` tools under `~/.claude/settings.json` (see `update-config` skill for the settings shape).
2. Parse the `command` input for top-level `&&` / `;` separators. Deny with a message naming the rule and telling Claude to split into separate calls.
3. Resolve the `|` question first - it is the reason this can't be a one-line regex. Recommended: **allow** `|` (it is a single command feeding a filter, not a chain) and block only `&&` and `;`. Confirm with Joe before implementing, since the written rule currently says otherwise; if he wants `|` blocked too, the hook needs an allowlist for `Select-Object`/`Measure-Object`/`ForEach-Object` and for the `/commit` prefilter.
4. Do not flag `;` or `&&` inside quoted strings or heredocs (the comment-noise awk script contains both).

## Acceptance
- A `Bash` call containing `cd X && git status` is denied with a message citing the rule.
- A `PowerShell` call containing `flutter analyze | Select-Object -Last 5` still runs (assuming the step-3 decision is "allow `|`").
- The `/commit` skill's comment-noise prefilter command still runs unblocked.

## Notes

Relocated from 66 in zng-biller via /cleanup-todos 2026-08-13: targets the global ~/.claude/settings.json hook wiring, nothing zng-biller-specific in the fix itself.
- Archived 2026-08-13 as DECLINED, and the premise is dead. This is the SIXTH filing of the same request; done/ already holds 07, 21, 64, 79, 208 and 267, and 267 was itself dropped on 2026-08-12. The rule it would enforce no longer exists: commit b28c296, 'CHORE: retire the never-chain-shell-commands rule', deleted the line from CLAUDE.md on 2026-08-11 at Joe's explicit direction, verified this run by reading that commit's diff. It reached this backlog by being relocated from zng-biller, a path that skips the content-duplicate guard, which is now filed as todo 313. The spike was still built and measured before that was discovered, and the numbers are worth keeping so a seventh filing can be closed instantly: against 30047 unique real commands pulled from this machine's own transcripts across ~50 projects, a naive detector flags 55 percent, and roughly 80 percent of a hand-classified sample of 60 were false positives, mostly the 'cd X && command' directory-scoping idiom that is the only way to scope a command since cwd does not persist across tool calls. NOT WIRED. Prototype kept at hooks/EXPERIMENTAL-command-chaining-detector.py. It also surfaced a real gap: bash heredocs are not masked by the shared quote logic, which only handles PowerShell here-strings.
