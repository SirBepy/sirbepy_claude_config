<!-- Claim before executing: .claude/todos/.claims/992-seven-em-dashes-sit-in-two-skill-files.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=3, reconfirm-count=1, content-hash=d5c08c77 -->
<!-- duplicate-checked -->
<!-- checked against 290 and 791, both in done/. 290 is about a builder emitting em dashes in NEW
     output despite the rule being in its dispatch; 791 is about the prefilter requirement living
     only in prose and not in the pasted preamble block. Both concern newly written lines. This is
     about lines already committed that no check looks at. Different cause, different fix. -->
# Seven em dashes sit in two skill files, where the rule says there are none

**Type:** task
**Origin:** ai

## Goal

Remove the em dashes already committed in `skills/commit/SKILL.md` and `skills/linear/SKILL.md`, or
decide deliberately that pre-existing ones are out of scope and say so where the rule is stated.

## Context

Found 2026-09-12 by a `/code-check` reviewer and confirmed directly. Exact locations:

- `skills/commit/SKILL.md`: lines 51, 53, 54, 55, 154
- `skills/linear/SKILL.md`: lines 34, 80

Global `CLAUDE.md` states the rule without qualification: "Never use the em dash character anywhere,
ever." `skills/bepy-skill-creator/SKILL.md` carries it as a FAIL-checklist row for skill files
specifically.

**This is not an enforcement failure; it is the enforcement working as designed.**
`skills/commit/em-dash.sh` only inspects ADDED lines in a diff, which is a deliberate choice
recorded in `/commit` step 5a: "the script only looks at added lines, so a pre-existing em dash on
an unchanged line never gets reported and needs no exception." That keeps a one-line edit to an old
file from dragging in unrelated churn. The cost is that anything already committed stays forever,
invisible to every future commit.

Both files were touched during the 2026-09-11 run, but only in other regions: one paragraph in
`commit/SKILL.md` and the frontmatter `description` in `linear/SKILL.md`. Verified that the range
`135d6cb..HEAD` added zero lines containing an em dash, so this is genuinely inherited debt and not
something that run introduced.

It was deliberately NOT fixed in passing during that run's `/close`. Silently reversing a documented
design decision about which lines the checker looks at is not a drive-by edit's job, and CLAUDE.md's
"every changed line must trace to the request" cuts the same way.

## Approach

1. Re-measure before editing; line numbers move. Scanning `skills/**/*.md` for U+2014 costs
   nothing and tells you whether the population is still seven or has grown. Use the codepoint,
   not a literal, or this todo's own prefilter will flag your grep pattern.
2. Replace each with a comma, colon, or hyphen, picking per sentence rather than substituting one
   character globally. Several sit between a term and its explanation, where a colon reads better
   than a hyphen, and a blind replace produces worse prose than the character it removed.
3. Do not change the scope of `em-dash.sh`. Making it scan whole files rather than added lines would
   mean every commit touching an old file now has to clean that file first, which is the churn the
   added-lines-only rule was chosen to avoid. If that tradeoff is worth revisiting, that is its own
   decision and its own todo.
4. Consider whether a one-off sweep of all skill files is worth doing at the same time, since the
   marginal cost after the first two files is small. Decide from step 1's count.

## Acceptance

- `skills/commit/SKILL.md` and `skills/linear/SKILL.md` contain no em dash.
- Replacements were chosen per sentence; no single global character substitution.
- `em-dash.sh` behaviour is unchanged.
- `python ci/run_all.py` passes.

## Notes

- Low urgency and purely cosmetic in effect, but the rule is stated as absolute, and a stated
  absolute that is visibly false in the repo's own files is what erodes the rest of them.
- These are prose files: no test can catch a regression here, so the check is a re-scan, not a suite.
