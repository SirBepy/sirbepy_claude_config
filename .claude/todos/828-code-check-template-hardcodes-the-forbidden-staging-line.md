<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=HARD, worth=7, reconfirm-count=2, content-hash=030486db -->
<!-- duplicate-checked -->
<!-- Searched this backlog and done/ for "staging line", "unstaged", "preamble", "dispatch marker".
     784 / done-364 / done-373 / done-392 all cover templates MISSING a marker. None covers a
     template that hardcodes the wrong VARIANT of one it already has. -->
# /code-check's dispatch template hardcodes the staging line shared-index repos forbid

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `/code-check`'s dispatch block from prescribing a staging instruction that global `CLAUDE.md`
forbids in shared-checkout repos, and stop it implying the hook demands that exact wording.

## Context

`skills/code-check/SKILL.md`'s dispatch block hardcodes:

```
Stage your changes but do NOT commit. The main agent will run /commit after your report-back.
```

and introduces the block as "The three preamble markers below are required by
`hooks/dispatch-preamble-guard.py`".

Global `CLAUDE.md`, Git Commits, says the opposite for this class of repo: the default line is used
by default, but "for a shared-index repo (e.g. zng-app, zng-biller) substitute 'Leave all changes
unstaged. The main agent will run `/commit` by pathspec after your report-back.'"

**The hook accepts either variant.** Confirmed 2026-08-27 by reading
`.claude/todos/784-four-more-dispatch-templates-still-miss-the-guard-markers.md:35`
("`Stage your changes but do NOT commit` OR `Leave all changes unstaged`") and the same pairing in
`done/364`, `done/373` and `done/392`. So there is no real conflict - only the SKILL.md text
presents one variant as mandatory.

Cost when it fires: running `/code-check` in zng-app on 2026-08-27, the dispatch was sent with the
hardcoded line *plus* a hand-written parenthetical undoing it, because the guard was believed to
require the literal string. Redundant, and a session that resolved the conflict the other way would
have told a subagent to `git add` inside a checkout three other sessions were committing from.

## Approach

1. In `skills/code-check/SKILL.md`, replace the hardcoded staging sentence with both variants and a
   one-line rule for picking (shared `.git` / concurrent sessions -> the unstaged form).
2. Fix the surrounding claim: say the guard requires *a* staging line and accepts either wording,
   not that these exact three strings are required.
3. Grep the other skills that embed a dispatch preamble for the same hardcoding - `/close`'s own
   Phase 2 text, `mega-todos`, `rate-it`'s `panel.md`, `delegate`, `autopilot` - and give them the
   same treatment rather than fixing one.
4. Cheaper alternative worth weighing first: put the staging line in ONE shared snippet the
   templates reference, so this cannot drift per skill again. That overlaps
   `472-mega-todos-builder-block-is-hand-copied-per-dispatch`; check whether these should merge.

## Acceptance

- No skill hardcodes a staging line without naming the shared-checkout alternative.
- `hooks/dispatch-preamble-guard.py` still passes a dispatch using either variant, verified by
  running its self-test.
