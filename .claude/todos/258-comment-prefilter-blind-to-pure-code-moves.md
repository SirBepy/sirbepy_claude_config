<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=HARD, worth=8, reconfirm-count=2, content-hash=56a61aab -->
# Comment-noise prefilter has no carve-out for pure code moves, so agents delete real documentation

**Type:** skill-improvement
**Origin:** ai

## Goal

The `/commit` comment-noise prefilter cannot distinguish a newly-authored comment from a
pre-existing one that moved to a new file. On a pure code move it fires on essentially every new
file, and agents obey it by deleting documentation. Give the rule an explicit carve-out.

## Context

Observed 2026-08-11 in `claude_usage_in_taskbar`, during a `/mega-todos` run of seven parallel
`split-*` refactor todos (commits `51265635`, `25f03dca`, `14f588c9`, `23d00c9b`, `e30d4a02`,
`ef463192`, `c9f0d4aa`). Every builder was told two things:

- from the lane spec: "This is a pure code MOVE - carry existing comments across unchanged"
- from the injected `/commit` block, step 3: run the awk prefilter and "If it prints anything, TRIM
  those blocks to the cap. Do not ask, just trim."

Those conflict. `git diff` sees a moved file's pre-existing comments as ADDED lines, so the
`add[k]>=20 && c[k]*100/add[k]>=25` density test and the `max[k]>=5` longest-run test both fire on
files where not one comment line was authored. Reported densities that run: `close.rs` 29%,
`lifecycle/teardown.rs` 27%, `bootstrap/watchdogs.rs` 20%, `history_page.rs` 12% with a 17-line run.

Four of seven agents flagged the conflict in their report. Three resolved it by trimming; three of
the trimmed clauses were constraint-bearing (a function-coupling constraint, a transcript-format
fact, a trigger condition) - precisely what the cap rule exists to protect. Four agents refused to
trim and said why, which is the correct behavior and shows the instruction is genuinely ambiguous
rather than simply ignored.

The repo-side restoration is filed separately as
`claude_usage_in_taskbar/.claude/todos/609-restore-doc-comments-trimmed-during-code-moves.md`. This
todo is only about the global rule and the prefilter.

Related: `~/.claude/refs/` memory `feedback_subagents_degrade_product_to_pass_tooling` - a reported
workaround is the highest-signal line in a subagent report. That heuristic is what caught this.

## Approach

The awk prefilter cannot detect a rename on its own (it reads `git diff HEAD` and `--no-index`
output for untracked files, neither of which carries rename detection here), so fixing the awk is
the wrong layer. Fix the instruction instead.

1. In `~/.claude/skills/commit/SKILL.md`, at the prefilter step, add: a prefilter hit on a file whose
   added lines are a VERBATIM MOVE from another file in the same commit is expected and must not be
   trimmed. Verify by diffing the moved block against its source (`git show HEAD:<old file>`) before
   dismissing - the exemption covers unchanged text only, not newly written comments in a moved file.
2. Mirror the same sentence into `~/.claude/skills/mega-todos/SKILL.md`'s injected commit block,
   since builder agents only ever see that pasted copy and never read the skill file.
3. Consider whether the global `CLAUDE.md` comment-cap section should say the same thing once, with
   both skills pointing at it, rather than stating it twice.

Rejected: teaching the awk to detect renames via `git diff -M --find-copies`. It would need the full
commit's rename map before the commit exists, and the prefilter runs against the working tree.

## Acceptance

- A builder agent handed a pure-move task and the injected commit block does NOT trim moved comments,
  and says so.
- The exemption is explicitly scoped to verbatim moves - a newly authored 6-line comment in a new
  file is still a hit.
- Re-reading the two skill files, the rule appears in both places an agent could encounter it.
