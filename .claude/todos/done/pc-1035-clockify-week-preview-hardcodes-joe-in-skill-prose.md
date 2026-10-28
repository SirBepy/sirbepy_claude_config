<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=3, reconfirm-count=1, content-hash=d6318b30 -->
<!-- duplicate-checked: the guard's hits (1008, 1016, 1017, 997, 285) are all unrelated clockify-reconciliator findings that only share the "clockify/reconciliator/skill" vocabulary; none of them discuss the FAIL-checklist hardcoded-name rule or Joe-attribution wording. -->
# clockify-reconciliator's week-preview rewrite hardcodes "Joe" in new SKILL.md prose

**Type:** skill-improvement
**Origin:** ai

## Goal

Decide, then apply, how the 2026-09-28 week-preview rewrite in
`skills/clockify-reconciliator/SKILL.md` should name the dev in its newly-added lines, given a
real conflict between two rules that both apply to this file.

## Context

`bepy-skill-creator/SKILL.md`'s FAIL checklist: "No hardcoded user names (e.g. \"Joe\"). Use \"the
dev\", \"the user\", or \"you\" instead. Personal names leak identity and reduce portability." The
2026-09-28 diff adds three lines that breach this literally:

- `SKILL.md:70` - `Joe, 2026-09-25: "pls update the skill so that hubstaff only fires..."`
- `SKILL.md:269` - `Joe (2026-09-28): "whenever I use that skill, I'll always see the same
  website, just with different figures."`
- `SKILL.md:313` - `Joe rejected a horizontal one-bar-per-day shape on sight (2026-08-27)`

But this is not a stray slip - it's the file's established house style. Untouched pre-existing
lines in the same file do the identical thing, e.g. `SKILL.md:140`: `Joe, 2026-08-27: "count all
the hours of a project"`. The whole skill corpus uses dated, attributed dev quotes as
decision-provenance anchors, load-bearing enough that CLAUDE.md's Execution Discipline section
explicitly defends the pattern elsewhere ("Falsified theories are worth saving... Record the
evidence and an absolute date, never a bare verdict").

Surfaced by `/code-check` (dispatched from a zng-app session, scoped to this file) as a
class-3 judgment finding: a mechanical find-replace of just the 3 new instances would leave the
file inconsistent with its own many older "Joe, DATE: ..." lines, so this needs a real decision,
not an auto-apply.

## Approach

Pick one, deliberately, then apply it consistently to the whole file (not just the 3 new lines):

1. **Keep "Joe" throughout** - this skill is single-dev, Cinnamon-specific tooling that will
   likely never be portable/shared, and the provenance value of a named, dated quote outweighs
   the portability rule here. If chosen, this todo should also flag the pattern to
   `bepy-skill-creator/SKILL.md`'s own author as a case the FAIL rule may want an explicit
   exception for (single-dev personal-tooling skills), so the same tension doesn't get
   re-discovered on the next `/code-check` pass over this file.
2. **Reword every instance to "the dev"** - `the dev, 2026-09-25: "..."`, `the dev (2026-09-28):
   "..."`, `the dev rejected...` etc., across all existing instances in the file plus the 3 new
   ones, restoring literal compliance with the FAIL rule.

## Acceptance

- A decision is made and stated (which option, why).
- If option 2: every `Joe, ` / `Joe (` / `Joe ` dev-attribution instance in
  `skills/clockify-reconciliator/SKILL.md` is reworded consistently, not just the 3 new ones from
  this diff.
- If option 1: this todo is closed as Won't Do with the reasoning above, and (optionally) a
  separate todo is filed against `bepy-skill-creator/SKILL.md` proposing the exception.

## Notes

- Dropped via /cleanup-todos 2026-10-05: worth 3/10, the 'Joe, DATE' attribution lines match a long-standing in-file convention; preference, not defect.
