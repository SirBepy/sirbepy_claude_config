<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# The comment rule caps length but says nothing about tense or narrative leakage

**Type:** task
**Origin:** ai

## Goal

Add the Timeless Present rule to the comment guidance, so comments stop narrating the change that
produced them, and make CLAUDE.md's enforcement levels legible at a glance.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`). Two separate
CLAUDE.md improvements, grouped because both are edits to the same file and both are about making
existing rules sharper rather than adding new obligations.

**1. The Timeless Present Rule** (`repos/solatis_claude-config/conventions/temporal.md`)

"Comments must be written from the perspective of a reader encountering the code for the first time...
the code simply IS."

The existing Code Style rule caps comments at 2 lines typical / 4 hard / under ~25% of added lines,
and bans narrating what the next line does or restating a name. It says nothing about **tense or
change-relative framing**, which is a different failure. A comment can be one line, name a real
constraint, and still be wrong:

`// Added mutex to fix race condition` becomes `// Mutex serializes cache access from concurrent requests`

The first is a changelog entry stranded in the source. Six months later the reader does not know what
race, does not care that it was added, and cannot tell whether the mutex is still needed. The second
states the invariant.

`temporal.md` ships a 5-category detection heuristic with before/after tables: change-relative
("added", "now", "no longer"), baseline-reference ("unlike the old version"), location-directive ("see
above"), planning-artifact ("TODO from the refactor"), and intent-leakage ("we decided to"). That
taxonomy is what makes it enforceable rather than aspirational, and it maps onto the existing
"paragraph of design rationale belongs in the PR body" rule: same instinct, different axis.

This is a strong candidate for mechanical enforcement, since the commit flow already runs
`skills/commit/comment-noise.md` and `em-dash.sh` as prefilters over added lines. Change-relative
comments are grep-detectable in a way most style rules are not.

**2. Strength-tagged bullets** (`astral-sh/uv`'s 25-line `AGENTS.md`)

Every rule prefixed ALWAYS / PREFER / NEVER / AVOID, so enforcement level is part of the syntax
rather than inferred from prose weight. Examples: "NEVER update all dependencies in the lockfile and
ALWAYS use `cargo update --precise`", "NEVER assume clippy warnings or test failures are pre-existing."

This CLAUDE.md writes full sentences of similar-sounding weight throughout. Some rules are absolute
("Never use the em dash character anywhere, ever", "NEVER commit directly") and some are defaults
("Default to PowerShell", "Prefer the platform primitive"), but the distinction lives in the wording
rather than in a scannable marker. The relevant risk is the one recorded in the harvest: an unverified
report of a CLAUDE.md growing 45 to 190 lines with compliance dropping. Tagging does not shorten the
file but it makes priority survivable at length.

## Approach

1. Read `repos/solatis_claude-config/conventions/temporal.md` in full for the 5 categories and the
   before/after tables.
2. Add the Timeless Present rule to CLAUDE.md's Code Style section as an extension of the existing
   comment rule, not a new section. Keep it short: the principle plus the 5 category names. The
   before/after tables go in a ref if they are wanted, since CLAUDE.md is already the file this todo
   is trying not to bloat.
3. Extend the commit prefilter, which is where this rule actually gets teeth. `skills/commit/comment-noise.md`
   already scans added comment lines; add change-relative detection to it (the "added", "now",
   "no longer", "we decided", "unlike the old" family). Follow the existing prefilter convention:
   flagged means fix that line now, and the em-dash precedent (todo 290) shows a script beats
   restating the rule louder.
4. Check the false-positive rate before wiring it as a gate. Run the detector over the existing tracked
   tree and count hits. If it flags a lot of legitimate comments, it becomes advisory output rather
   than a blocker. Report the real number either way.
5. For strength tagging, do the audit first and treat it as the deliverable: classify every current
   CLAUDE.md bullet as ALWAYS / NEVER / PREFER / AVOID. That classification is useful on its own and
   will surface rules whose intended force is genuinely ambiguous, which is the real find.
6. Apply the tags only after the audit. This is a large mechanical edit to the most load-bearing file
   in the repo, so it should be its own commit with no other changes, and the diff should be
   tag-additions only.

## Acceptance

- The Timeless Present rule is in CLAUDE.md's Code Style section, within the comment budget the
  section itself imposes.
- The comment-noise prefilter detects change-relative comments, with the false-positive count over
  the existing tree reported as a real number.
- If the false-positive rate is high, the detector ships as advisory and that decision is written down.
- Every CLAUDE.md bullet carries a strength tag, and the tagging commit changes nothing but tags.
- No existing rule's meaning changes during tagging. A rule that was a default does not become
  absolute because ALWAYS read better.

## Notes

The tagging pass is the risky half. Re-reading 17 sections and assigning force is exactly where a
"Prefer" quietly becomes an "ALWAYS" and a soft default turns into a hard rule nobody agreed to. If
any rule's intended force is unclear, tag it PREFER and flag it rather than guessing upward.

Do the two halves as separate commits. They are unrelated and one is far riskier than the other.
- Done 2026-08-22. Half 1 shipped: Timeless Present in CLAUDE.md plus skills/commit/comment-tense.sh in the prefilter gate, 1 false positive across 86 tracked code files after 'no longer' and 'previously' were measured at 36 mostly-legitimate hits and cut. Half 2 SKIPPED by design: tags were not applied, the audit ran instead and is in refs/claude-md-rule-force-audit.md. It found 4 entries that are not rules, exactly 1 bullet with two forces in one sentence, and exactly 1 genuine AVOID in 81 bullets, so the prose already carries the distinction in 76 of 81. Re-open trigger recorded in that file.
