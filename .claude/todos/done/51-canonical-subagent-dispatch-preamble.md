<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- relocated: filed 2026-08-01 under shop-scraper's .claude/todos/29-*, moved here 2026-08-08 by /auto-do-todos per CLAUDE.md's "global work belongs in ~/.claude/todos/" rule -->
<!-- cleanup: last-checked never, complexity=unknown (shallow pass), reconfirm-count=1, content-hash=- -->
# Give the delegation doctrine a canonical dispatch preamble

**Type:** skill-improvement

## Goal

Stop hand-writing the same subagent ground-rules block on every dispatch. It was retyped ~14
times in one session, and the one rule that got left out of it caused a real contract breach.

## Context

Found 2026-08-01 during `/close` retrospective of a long `/auto-do-todos` + `/delegate` +
`/autopilot` session in shop-scraper.

`~/.claude/refs/delegation-doctrine.md` lists what "every builder prompt embeds, without
exception": the verify floor, the verbatim stage-don't-commit line, restated global rules
(PowerShell, no `&&`/`;`/`|` chaining, working directory), the orphan-check, the
no-`run_in_background` line, and the no-`git stash`/`reset`/`checkout` line. It states the
requirement but provides no copy-able text, so each dispatch reconstructs it from memory.

**The concrete failure this caused.** Global CLAUDE.md mandates that throwaway verification
screenshots go in `.for_bepy/screenshots/<claude-ancestor-pid>/`, a per-session subfolder, so
`/close` can prove ownership by subfolder and purge only its own. That rule is NOT in the
doctrine's embed list, so it was not in any dispatch prompt. Two agents were instead told to
write to `.for_bepy/screenshots/favicon-candidates/` and `.for_bepy/screenshots/favicon-cart/`.
Result: seven files that `/close` could not prove ownership of and therefore could not clean up,
left on disk indefinitely. The orchestrator wrote the wrong path into the prompt itself, so no
amount of subagent diligence could have caught it.

Reconstructing from memory also produced drift: some dispatches got the orphan-check line, some
did not; the OFF LIMITS file list was correctly tailored per dispatch but the boilerplate around
it varied for no reason.

## Approach

1. Add a `## Canonical builder preamble` section to `~/.claude/refs/delegation-doctrine.md`
   containing the literal block to paste, with `<WORKING_DIR>` and `<OFF_LIMITS>` placeholders.
   The per-dispatch parts (task, scope, verify floor specifics) stay hand-written, since those
   are the parts that actually need thought.
2. Add the screenshot-subfolder rule to that block, with the real path shape
   `.for_bepy/screenshots/<claude-ancestor-pid>/`, since a subagent cannot resolve the ancestor
   pid itself and must be handed it.
3. Audit the rest of global CLAUDE.md for other rules that a subagent must be told because it
   does not inherit session context. Candidates: the comment budget (currently retyped by hand
   every time), the "never suggest/add a package without the advisory-DB check" rule, and the
   Phosphor-icons rule for any frontend work.
4. Keep it short. If the preamble grows past what is genuinely load-bearing it will get skipped,
   which is worse than it being incomplete.

## Acceptance

- The doctrine contains a paste-able preamble covering every rule it already claims is mandatory.
- The screenshot subfolder rule is in it, with the pid placeholder called out as
  orchestrator-supplied.
- A dispatch written from the doctrine alone produces screenshots in a path `/close` can purge.

## Notes

- 2026-08-08: added `## Canonical builder preamble` to `refs/delegation-doctrine.md:67-100`, a paste-able block covering PowerShell/chaining/working-dir, the commit line, git stash/reset/checkout ban, the resolved `.for_bepy/screenshots/<ancestor-pid>-<ancestor-start-ticks>/` path, and the no-run_in_background line. Kept it a reference block (doesn't restate "Dispatch discipline" or model-tier rules, which the file already defers to global CLAUDE.md).
