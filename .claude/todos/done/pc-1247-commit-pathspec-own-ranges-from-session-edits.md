<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1245 is about a whole-file own-range defeating the check; this one is about callers hand-deriving real ranges with an awk one-liner every commit. Same root (ranges are tedious), different fix. -->
# Give commit-pathspec a helper that prints a file's current hunk ranges in `--own-range` form

**Type:** skill-improvement
**Origin:** ai
**Summary:** A helper prints a file's current hunk ranges in the form commit-pathspec expects, so callers stop retyping the same awk pipeline.

## Why

Claude derived ranges by hand about eight times in dashboard-a and wrote a throwaway script in the Conductor repo; the tedium pushes callers toward whole-file ranges.

## Goal

Stop every shared-checkout commit from re-typing the same awk pipeline to turn `git diff -U0` hunk headers into an
`--own-range file:a-b,c-d` argument.

## Context

- dashboard-a, 2026-10-24 to 25 (OVH trial chat): with 2+ live session markers, `commit-pathspec.sh` refuses
  multi-hunk files without `--own-range`. Claude derived the ranges by hand about eight times with
  `git diff -U0 -- f | grep '^@@' | sed -E 's/^@@ -[0-9,]+ \+([0-9]+)(,([0-9]+))? @@.*/\1 \3/' | awk ...`, including
  a 24-hunk `pnpm-lock.yaml`. Tedious work like this is what pushes callers toward `1-9999` (todo 1245).
- claude_usage_in_taskbar, 2026-10-26 (API-credit chat). The same pain hit a second repo, and
  Claude wrote a throwaway `.for_bepy/commit-own.sh` that dry-runs `commit-pathspec.sh`, scrapes
  its `auto-derived own-range ... UNVERIFIED` lines, and re-runs with them as `--own-range`. It was
  used for six commits of up to 29 files each, after reviewing every hunk by grep. That shows the
  script already computes the ranges itself, so the helper can reuse that derivation instead of a
  new awk pipeline.
- claude_usage_in_taskbar, 2026-10-28 ("AI todos view" chat, third recurrence). With 15 live session
  markers, five commits of subagent-written files (20 to 24 files each, in this repo and in
  `~/.claude`) needed a throwaway `.for_bepy/own-ranges.py` that turns `git diff -U0 HEAD` headers
  into `--own-range` args. A per-file "every current hunk is mine" flag (e.g. `--own-file <path>`,
  naming the file is the claim) would have covered every case there.
- The ranges still need a human judgement ("are all these hunks mine?"), so the helper must print, not auto-claim.

## Approach

Add `skills/commit/hunk-ranges.sh <files...>` that prints, per file, the `--own-range` argument for its current hunks
plus each hunk's first changed line, so the caller reads them and passes only the ones it owns. Mention it in
`skills/commit/SKILL.md` step 8 next to `--own-range`.

## Acceptance

A self-test creates a file with two separate hunks and checks the printed argument equals `file:a-b,c-d` with the right
numbers; `ci/run_all.py` passes.

## Notes

- Fixed in cdfe1e6 (hunk-ranges.sh helper).
