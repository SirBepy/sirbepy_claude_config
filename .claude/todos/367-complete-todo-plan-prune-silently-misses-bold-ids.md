<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# `complete-todo.ps1` never prunes a PLAN.md line written in the bold style, and says so as if it succeeded

**Type:** skill-improvement
**Origin:** ai

## Goal

Make the PLAN.md prune step actually match the lines PLAN.md really contains, and make a non-match
read as a warning rather than as a normal outcome.

## Context

Measured 2026-08-17: five consecutive `complete-todo.ps1` calls (todos 352, 354, 358, 359, 361) each
printed

```
No PLAN.md line found for todo <id> - nothing to prune.
```

and every one of those todos DID have a PLAN.md line. All five stale lines survived, and were only
removed because the session happened to rewrite PLAN.md by hand afterwards. Without that, five
archived todos would still be sitting in the To-Do lane pointing at files in `done/`.

The cause is `skills/close/complete-todo.ps1:219`:

```powershell
$lineIdPattern = "^\s*-\s*\[\s*\]\s*0*$([regex]::Escape($numericId))(\s|$)"
```

The id must follow `- [ ] ` with only whitespace between. PLAN.md's actual lines are

```md
- [ ] **352** - `/autopilot` and `/delegate` still carry the commit-cadence ambiguity
```

so the `**` defeats the match. Note this is a genuine two-sided conflict, not simply a bad regex:
`close/ai-todos-format.md`'s PLAN.md section specifies the plain form `- [ ] <id>`, so the bold
style is technically the deviation - but that same section also says to "parse forgivingly (stray
whitespace, hand-edits)", and multiple past runs have written the bold form, so it is the de facto
format in this backlog today.

The second half of the defect is the reporting. `Write-Info "No PLAN.md line found"` is the same
severity as every other success line the script prints, so a caller reading the output sees five
green-looking messages. A prune that finds nothing when a line exists is exactly the case that needs
to be loud.

## Approach

1. Widen the pattern to tolerate the markdown the backlog actually uses: optional `**`/`__`/backtick
   wrapping around the id, and the `[P]` parallel marker the format doc also allows. Keep the anchor
   and the `0*` zero-padding tolerance.
2. Decide, and write down in `ai-todos-format.md`, whether the bold form is now blessed or is to be
   normalized away. Either answer is fine; leaving both in circulation is what produced this.
3. Change the miss path from `Write-Info` to a distinct warning, and have it say what it searched for,
   so the next silent miss is visible in the output rather than inferred later from a stale PLAN.md.
4. Sweep PLAN.md for lines whose todo already lives in `done/` and remove them. The format doc already
   says a vanished id is silently pruned by the next reader; that never happened here because the
   reader was this same broken matcher.

## Acceptance

- Archiving a todo whose PLAN.md line is written `- [ ] **352** - label` removes that line.
- The plain form `- [ ] 352 - label` still works (do not trade one format for the other).
- A genuine no-line-exists case still reports, but distinguishably from a match-and-prune.
- Verified by running the script against a scratch PLAN.md containing both styles.

## Notes

- Filed 2026-08-17 by `/close` Phase 1 from a five-for-five failure in one `/auto-do-todos` run.
- Related: [[10-archiving-a-todo-needs-a-bespoke-script-every-time]] and
  [[102-claim-todo-script-counterpart]] in `done/`, which created this script and its sibling.
