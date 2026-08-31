<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=8, reconfirm-count=2, content-hash=02e79ae4 -->
<!-- duplicate-checked -->
# /commit step 8's overlap-check.sh silently exceeds the 120s Bash default on a large pathspec

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `/commit`'s unpushed-overlap check from being auto-backgrounded by the harness on a wide
pathspec, which turns a required gate into a killed command the caller has to notice and retry.

## Context

2026-08-27, committing 50 paths in `~/.claude` while 64 commits deep on an unpushed branch.

`bash skills/commit/overlap-check.sh -C <repo> <50 files>` ran past the Bash tool's 120s default and
was killed at the 2-minute mark with exit 143, having printed nothing past its header. Re-running the
identical command with an explicit `timeout: 600000` completed and returned exit 1 with 17 real
hunk-level hits, so the check works, it is just slow at that width. The cost is inherent: the script
does a file-level pre-filter against `@{u}..HEAD` and then a per-file hunk-range `git blame`, so
runtime scales with pathspec size times unpushed-commit count.

The failure is quiet in the worst way. A killed command looks like a failed check rather than an
unfinished one, and `refs/builder-preamble.md` already warns that "the harness auto-backgrounds past
it, so omitting `timeout` backgrounds your build whether you intended it or not" - but `/commit`
step 8, which is where this script is actually invoked, carries no such warning.

Verified against the working tree 2026-08-27: `skills/commit/SKILL.md` step 8's unpushed-overlap
bullet gives the invocation `bash ~/.claude/skills/commit/overlap-check.sh -C <repo> <files>` and
documents exit 0/1/2, with no mention of runtime or of passing a timeout.

Distinct from `done/474-commit-step-8s-overlap-check-should-be-a-script.md`, which created the
script and is complete. This is a new operational gap on top of that work, not a re-file of it.

## Approach

Cheapest fix first, and it may be enough:

1. Add one clause to step 8's unpushed-overlap bullet in `skills/commit/SKILL.md`: this call scales
   with pathspec size times unpushed-commit depth and must be given an explicit `timeout` (600000ms)
   whenever the pathspec exceeds roughly a dozen files, because the tool default of 120s will
   background it and a backgrounded gate is an unrun gate.
2. Optionally have `overlap-check.sh` print a one-line progress or count header early
   (`checking N files against M unpushed commits`) so a caller can tell "slow" from "hung" before
   the kill lands.
3. Only if 1 and 2 prove insufficient: batch the per-file blame, or short-circuit files whose
   file-level pre-filter found no candidate commit at all, which is the common case.

Do not raise the tool default or wrap the call in a background job - the gate has to complete before
`git commit` runs, which is exactly why step 8 chains them with `&&`.

## Acceptance

- `skills/commit/SKILL.md` step 8 names the timeout requirement at the point of invocation.
- A 50-file pathspec on a branch 60+ commits ahead completes the check without being killed.
- Must not regress: the `prefilter-gate.sh <files> && git commit` chaining in step 8, and the exit
  0/1/2 contract, both stay as they are.

## Notes

- Surfaced during the same run as `[[818-finish-the-cleanup-todos-triage-for-76-unmarked-todos]]`.
- Done via /mega-todos batch 1, commit 528ed99: /commit step 8 now requires an explicit timeout on overlap-check.sh whenever the pathspec exceeds roughly a dozen files, because the Bash default backgrounds it and a backgrounded gate is an unrun gate.
