<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# Resolve /commit's comment-noise pipeline vs the global no-chaining rule

**Type:** skill-improvement

## Goal

Remove the internal contradiction: `skills/commit/SKILL.md`'s Rules say "Never chain commands. No `&&`, `;`, or `|`" while step 5a mandates running the `git diff | awk | sort` prefilter pipeline from `skills/commit/comment-noise.md` verbatim on every commit.

## Context

Flagged by the 2026-08-01 skill audit (originally commit SKILL.md:152 vs step 5a's cross-load of create-pr's prefilter) and still present after the aux-file split moved the pipeline into `skills/commit/comment-noise.md` (shared with /create-pr). The no-chaining rule exists for permission-matcher/safety reasons (see memory reference_powershell_pipe_matcher). The pipeline runs fine via the Bash tool today - the conflict is doctrinal, and the 2026-08-01 session simply ran it and noted the tension.

## Approach

Either (a) carve an explicit sanctioned-exception line into commit/SKILL.md's Rules ("the comment-noise prefilter is the one permitted pipeline, run via Bash"), or (b) port the prefilter into a standalone script (`skills/commit/comment-noise.sh` or `.ps1`) invoked as a single command from both /commit step 5a and create-pr's drafting-rules. (b) is cleaner long-term; keep the awk logic byte-equivalent and update comment-noise.md to point at the script.

## Acceptance

- No self-contradiction between commit/SKILL.md Rules and step 5a.
- Prefilter still runs on every commit and still shares one definition with /create-pr (no re-duplication).

## Notes

- Duplicate of 45 - merged during /cleanup-todos 2026-08-11. Confirmed by dev 2026-08-11.
