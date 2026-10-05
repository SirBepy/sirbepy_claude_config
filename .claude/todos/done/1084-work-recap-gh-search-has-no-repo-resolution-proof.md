<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=EASY, worth=6, reconfirm-count=1, content-hash=b0d9eb9b -->
<!-- duplicate-checked: 1040 (done) fixed the same pattern in refs/outbound-ground-check.md only; 299 is zirtue group inference; this is the leftover call sites in work-recap/fibo -->
# work-recap's gh pr list --search has no repo-resolution proof

**Type:** task
**Origin:** ai

## Goal

`/work-recap`'s Fibo daily and weekly recipes cannot report "no PRs" when `gh` simply failed to
resolve the repo.

## Context

Todo 1040 (done, a38ce71) established that `gh pr list --search` answers an unresolvable repo with
`[]`, byte-identical to a genuine empty result, and added a `gh repo view` proof step to
`refs/outbound-ground-check.md`. The same pattern sits in `skills/work-recap/fibo/daily.md:58,64` and
`skills/work-recap/fibo/weekly.md:57,63` (`gh pr list --repo Fibo-Studio/fibo --search ...`). The repo
is hardcoded rather than cwd-inferred, so the risk is lower: it bites only if that repo stops
resolving under the active gh account.

## Approach

Add one `gh repo view Fibo-Studio/fibo --json name` line before each search block, and have a failure
print "PRs: UNVERIFIED (gh could not resolve Fibo-Studio/fibo)" instead of an empty list. Reuse the
wording from refs/outbound-ground-check.md rather than restating its rationale.

## Acceptance

- Both files run the resolution check before their searches.
- A failed check produces an explicit UNVERIFIED line in the recap, never a silent empty section.

## Notes

- Done in loop-todos cycle 2 (2026-10-06): fibo daily.md and weekly.md run gh repo view Fibo-Studio/fibo before the PR searches and report PRs as UNVERIFIED when it fails, mirroring todo 1040.
