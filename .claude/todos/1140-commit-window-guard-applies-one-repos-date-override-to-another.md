<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-08; no live or done todo covers commit-window-guard's override scoping -->
# commit-window-guard applies one repo's --date override to every repo in a chained command

**Type:** task
**Origin:** ai

## Goal
A timestamp override only counts against the commit it belongs to, so a plain daytime commit to a
client repo is never refused because of another repo's `--date` in the same shell chain.

## Context
Found by the loop-todos final review (2026-10-08, commit fce4a26), reproduced by the reviewer:
`hooks/commit-window-guard.py` `date_overrides()` (around line 186) scans the whole raw command for
`--date=` / `GIT_AUTHOR_DATE` / `GIT_COMMITTER_DATE`, and `main()` applies that one list to every
client-repo root it finds. At 14:00, `git -C <personal-repo> commit --date="2026-10-06 02:30:00" -m x
&& git -C <client-repo> commit -m y` is denied with "timestamp override (2026-10-06 02:30:00) lands
inside the 23:00-10:59 window", although the client repo's own commit has no override.

False-positive direction only: the list is a superset, so it can over-block but never miss a real
override. The guard's own tests only cover single-target commands.

## Approach
Collect overrides per chained segment (the guard already resolves each segment's target repo) and
check each client repo only against the overrides in its own segment, plus any env-prefix override
that applies to the whole command. Add the two-repo chain above as a test in
`hooks/test_commit_window_guard.py`. Live guard: one complete edit, run its test file right after.

## Acceptance
- The two-repo chain above is allowed at 14:00.
- `git -C <client-repo> commit --date="2026-10-06 02:30:00" -m y` at 14:00 is still denied.
- `python hooks/test_commit_window_guard.py` passes.
