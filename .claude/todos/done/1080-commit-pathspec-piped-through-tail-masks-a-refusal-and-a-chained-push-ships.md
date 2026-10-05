<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=EASY, worth=8, reconfirm-count=1, content-hash=acc18379 -->
<!-- duplicate-checked: 1076 is personal-repo overlap refusals, 1065 flutter client push gate, 994 short expect-sha, 1070 push-read-gate re-blocking; none cover a piped commit call's exit status being swallowed before a chained push -->
# commit-pathspec.sh piped through `tail` hides a refusal, so a chained `&& git push` ships without the commit

**Type:** skill-improvement
**Origin:** ai

## Goal
Make it structurally impossible for a `/commit pushnbump` run to push after `commit-pathspec.sh` refused the VERSION commit.

## Context
2026-10-05, claude_usage_in_taskbar session (release v0.2.112). Claude ran:
`bash ~/.claude/skills/commit/commit-pathspec.sh ... -m "VERSION: 0.2.112" -- package.json 2>&1 | tail -2 && git push origin master`.
commit-pathspec refused (`[foreign-hunk-check] UNVERIFIED, refusing (2 live session markers ...)`), but the pipeline's exit status was `tail`'s (0), so `git push` ran and shipped 7 commits WITHOUT the version bump. Harmless that time only because CI saw the existing `tauri-v0.2.111` tag and skipped the build. The bump was then committed with `--own-range` and pushed separately.
`skills/commit/SKILL.md` step 8 already warns about chaining with `&&` so a flagged diff can't reach the commit, but nothing covers output filters (`| tail`, `| head`, `| grep`) swallowing the script's own non-zero exit before a chained push.

## Approach
Pick one or both:
- `skills/commit/SKILL.md` pushnbump/push sections: state that the commit call must never be piped before a chained push. Run it unpiped, or with `set -o pipefail`, and check for its `[commit] committed` line before pushing.
- Better, mechanical: have `hooks/push-gate.py` (or the push-read gate) refuse a `git push` in the same command string as a piped `commit-pathspec.sh` call without `pipefail`. Or have commit-pathspec.sh write a marker that the push gate checks, so the gate confirms HEAD is the sha commit-pathspec just reported.

## Acceptance
Re-running the 2026-10-05 command shape against a refusing commit does not push. A test in `hooks/test_*.py` covers it.

## Notes

- Done in loop-todos cycle 2 (2026-10-06): skills/commit/SKILL.md step 8 says never pipe commit-pathspec.sh output and never chain a push after it; confirm from its exit code or the [commit] committed line. The mechanical push-gate marker (Approach's stronger option) was not built.
