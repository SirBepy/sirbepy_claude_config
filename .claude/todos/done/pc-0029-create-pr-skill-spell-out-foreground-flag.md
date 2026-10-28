<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-08, complexity=EASY, reconfirm-count=1, content-hash=a6d3a267 -->
# create-pr skill: spell out the actual tool parameter for its "foreground" step

**Type:** skill-improvement

## Goal

Close an enforcement gap in `~/.claude-personal/skills/create-pr/SKILL.md` (and any other skill
with the same phrasing pattern) so "foreground" dispatch instructions can't silently degrade to
background because the executing agent had to mentally translate an adjective into a tool
parameter and skipped it.

## Context

During the 2026-07-29 session that opened PR #186 (fix/pageheader-inline-toolbar), step 2 of
`/create-pr` says: "**Dispatch the drafting subagent (`general-purpose`, `model: 'sonnet'`) -
skip this step entirely if the size gate above routed to inline drafting.** One call,
**foreground** (its report is needed before anything else can happen)."

The executing session called the `Agent` tool without setting `run_in_background: false`. The
`Agent` tool defaults to background dispatch. Nothing in the call syntax or the skill text names
the actual parameter (`run_in_background: false`) - "foreground" is prose that has to be manually
mapped to that flag, and the mapping got skipped. It caused no visible harm this time (nothing
else was queued while waiting), but the whole reason step 2 is marked foreground is that later
steps in the SAME procedure (step 3's visual-approval gate) read the subagent's return value
before continuing - a background dispatch racing ahead into step 3 without the result would break
the flow silently.

A feedback memory was already written this session
([[feedback-dispatch-foreground-when-skill-says-so]]) as the immediate "remember next time" fix,
but per `/close`'s own guidance, a skill rule violation candidate should describe an enforcement
gap, not just a "be more careful next time" note - hence this todo.

## Approach

Grep `~/.claude-personal/skills/` and `~/.claude/skills/` for the word "foreground" in any
`SKILL.md`/step that dispatches via the `Agent` tool. For each hit, rewrite the instruction to
name the literal parameter instead of (or alongside) the adjective, e.g.:

> One call, **`run_in_background: false`** (foreground - its report is needed before anything
> else can happen).

`create-pr/SKILL.md` step 2 is the confirmed instance; check step 3's screenshot-capture subagent
dispatch too (it's a live gate dependency the same way). Search other skills opportunistically
while in there (`iterate-it`, `rate-it` panel dispatches, etc. may have the same pattern) but
don't scope-creep into a full skills audit - fix the ones actually found by the grep.

## Acceptance

- Every "foreground" dispatch instruction in a `SKILL.md` names `run_in_background: false`
  explicitly next to the word "foreground", not as a separate inference step.
- No behavior change to the skills themselves - this is a wording/enforcement fix only.

## Notes

- Moved out of the fibo backlog into ~/.claude/todos/ via /auto-do-todos 2026-08-07: this changes global Claude tooling, not fibo code, and root CLAUDE.md puts those here. Was fibo todo 171; renumbered to 29 per the max+1 id rule. Confirmed by dev 2026-08-07.
- 2026-08-08: named `run_in_background: false` next to "foreground" in create-pr/SKILL.md step 2 and added the same flag to step 3's screenshot subagent dispatch (same live-gate dependency, previously unmarked). Grep of `~/.claude/skills` found "foreground" in ios-run/SKILL.md and flutter-cicd/SKILL.md but neither is an Agent-dispatch step (terminal `flutter run --profile` and an `adaptive_icon_foreground` config key), so left untouched - scoped to create-pr only per this run's dispatch.
