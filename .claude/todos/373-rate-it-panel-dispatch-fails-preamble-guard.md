<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Following /rate-it's panel.md verbatim gets every dispatch rejected by dispatch-preamble-guard

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/rate-it`'s panel-mode dispatch prompt pass `hooks/dispatch-preamble-guard.py` on the first
try, so a panel run does not burn a full round of rejected tool calls before any rater starts.

## Context

Reproduced 2026-08-18 while running `/rate-it 4` during the todo 58 skills audit. `panel.md`'s
"Dispatch" section gives a verbatim prompt template to paste into each `Agent` call. Following it
exactly got **all four dispatches rejected in one shot**:

```
[dispatch-preamble-guard] Dispatch prompt is missing required preamble marker(s):
staging line ("Stage your changes but do NOT commit" or "Leave all changes unstaged");
run_in_background ... FORBIDDEN line; .for_bepy/screenshots/ id line (or the READ-ONLY
DISPATCH opt-out). Paste the canonical block from refs/builder-preamble.md before dispatching.
```

The template in `skills/rate-it/panel.md` (Dispatch section, the blockquoted prompt) contains none
of the three strings the hook hard-requires. The hook is global `PreToolUse` on `Agent`, so it fires
for every dispatch regardless of what the dispatching skill is for.

**This is the same failure class as [[364-mega-todos-commit-block-fails-dispatch-guard]]**, in a
different skill: a skill hands the agent a prompt template that a hook then rejects. 364 covers
`/mega-todos`' injected commit block only, so this is a sibling, not a duplicate. Worth checking
whether any OTHER skill embeds a dispatch template with the same gap while fixing this.

The rating panel is the cleanest case for the opt-out the guard already supports: raters read files
and return a score, they write nothing and capture no screenshots, so the literal `READ-ONLY
DISPATCH` marker documented in `refs/builder-preamble.md` ("Read-only opt-out") applies exactly.
That opt-out only waives the screenshot-id line though. The staging line and the
`run_in_background ... FORBIDDEN` line are still required, so the template needs all three.

## Approach

1. In `skills/rate-it/panel.md`, extend the Dispatch template so it carries, verbatim:
   - `READ-ONLY DISPATCH` on its own line
   - the staging line `Stage your changes but do NOT commit. The main agent will run /commit after your report-back.`
   - the `run_in_background` FORBIDDEN sentence from `refs/builder-preamble.md`
2. Prefer pointing at `refs/builder-preamble.md` as the paste source rather than re-typing the block,
   which is what that ref exists for and what stops this drifting again. Keep the read-only marker
   inline in panel.md, since it is a per-dispatch judgement the ref cannot make.
3. Note in panel.md that rating subagents must not write files, so the staging line is inert boilerplate
   the hook requires rather than a real instruction. Otherwise a future reader will delete it as wrong.
4. Sweep the other skills that embed an `Agent` dispatch template and check them against the same
   three markers. Start from `iterate-it`, `mega-todos` (already todo 364), `autopilot`, `delegate`,
   `auto-do-todos`, `code-check`.

## Acceptance

- A `/rate-it N <thing>` run dispatches all N raters with zero guard rejections.
- `hooks/dispatch-preamble-guard.py` is NOT modified. The hook is correct; the template is what is wrong.
- Any other skill found carrying the same gap is either fixed or has its own todo filed.

## Notes

- Cost when it fires: one wasted `Agent` tool call per rater, plus the orchestrator round-trip to
  read `refs/builder-preamble.md` and rebuild every prompt. On a 5-rater panel that is 5 rejected
  calls before any work starts.
- `done/221-fix-rate-it-panel-md-skill-path.md` already fixed a different bug in this same Dispatch
  section (a hardcoded `~/.claude` path). That section has now been wrong twice, which is an argument
  for making it reference `refs/builder-preamble.md` instead of carrying its own copy.
- Related: [[356-prefilter-and-commit-in-one-shell-call-has-no-gate]] and
  [[357-orphan-check-is-gated-on-node-so-a-plain-find-sweep-escapes-it]] are the other live findings
  about this guard family.
- **`autopilot` CONFIRMED to have the gap - Approach step 4 no longer needs to "check" it for that
  one (2026-08-18, `claude_conductor` session).** A 4-way `Explore` fan-out during an `/autopilot`
  run was rejected all four at once with the identical marker list. The mechanism differs from
  rate-it's though, and the fix has to differ with it: **autopilot embeds no dispatch template at
  all.** Its "Delegation doctrine" section says the run "ADOPTS `~/.claude/refs/delegation-doctrine.md`
  in full ... Read it at the start of the run", and that file in turn points at
  `refs/builder-preamble.md`. So passing the guard requires following a two-hop reference chain
  BEFORE writing the first dispatch prompt, at a moment when the orchestrator is usually mid-plan
  and reaching for `Agent` directly. Nothing fails until the hook fires, by which point every prompt
  in the fan-out is already written and must be rebuilt.
  Suggested fix for autopilot specifically: make the preamble requirement fire at the point of use
  rather than as a start-of-run reading assignment - e.g. name the three required markers inline in
  autopilot's own delegation section, so an orchestrator that never opened either ref still emits a
  passing prompt. Same "reference the ref, don't re-type the block" principle as step 2 above,
  applied one level up.
