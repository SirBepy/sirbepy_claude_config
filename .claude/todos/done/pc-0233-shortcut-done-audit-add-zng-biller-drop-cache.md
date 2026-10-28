<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=6, reconfirm-count=2, content-hash=4b0f4cfd -->
# shortcut-done-audit: add zng-biller to repo constants + both git loops, drop unused audit_cache.json machinery

**Type:** skill-improvement

## Goal

`skills/shortcut-done-audit/SKILL.md` only scans `zng-app`, `zng-admin`, `zng-api` for
matching commits - `zng-biller` is missing, even though the shared constants file
(`~/.claude/refs/shortcut-api.md`) already lists it as a repo. Add it to this skill's own
repo list and both places that loop over repos. Separately, the skill's dedupe-cache
mechanism (`state/audit_cache.json`) is speced in detail but never actually gets used in
practice - drop that machinery rather than carry dead complexity.

## Context

`skills/shortcut-done-audit/SKILL.md` (as of 2026-08-01):

- Line 38, "Repos (sibling paths)": `C:/Users/tecno/Desktop/Projects/zng-app`,
  `zng-admin`, `zng-api` â€” three repos, no `zng-biller`.
- Compare `~/.claude/refs/shortcut-api.md` lines 34-37, which already lists all four:
  `zng-app`, `zng-admin`, `zng-api`, `zng-biller`. This skill's own repo list has drifted
  from the shared constants file.
- Loop 1 (Step 1, "Refresh repos", lines 45-49):
  ```bash
  git -C C:/Users/tecno/Desktop/Projects/zng-app fetch --quiet
  git -C C:/Users/tecno/Desktop/Projects/zng-admin fetch --quiet
  git -C C:/Users/tecno/Desktop/Projects/zng-api fetch --quiet
  ```
  Missing a `zng-biller fetch --quiet` line.
- Loop 2 (Step 3, "Match candidates to commits", lines 63-69): iterates "across all three
  repos" with `git -C <repo> log --all --oneline -E --grep="^${id}:"` - the prose itself
  says "three repos" and needs to become "four," and the loop needs to include
  `zng-biller`.
- `audit_cache.json`: Step 4 (lines 77-84) and Step 8 (lines 103-105) describe reading
  and writing `state/audit_cache.json` (path per line 39: `C:/Users/tecno/.claude/skills/
  shortcut-done-audit/state/audit_cache.json`) as a dedupe mechanism so re-runs skip
  unchanged tickets. Per the skill audit this file has never actually been created/used
  across real runs to date - the caching logic adds real complexity (SHA-set comparison,
  cache-entry staleness, merge-on-write) for a benefit that hasn't materialized.

## Approach

1. Read `skills/shortcut-done-audit/SKILL.md` in full before editing.
2. Add `zng-biller` to the repo list (line 38 area), matching the path convention of the
   other three (`C:/Users/tecno/Desktop/Projects/zng-biller`).
3. Add a `git -C C:/Users/tecno/Desktop/Projects/zng-biller fetch --quiet` line to Step 1
   ("Refresh repos"), and update its "Stop and tell Joe if any fetch fails" note to cover
   all four repos.
4. Update Step 3 ("Match candidates to commits") to loop over all four repos instead of
   three - update the prose ("across all three repos" -> "across all four repos") and the
   git-log command's repo iteration.
5. Remove Step 4 ("Check the dedupe cache before dispatching anything") and Step 8
   ("Update the dedupe cache") in their entirety, and the `state/audit_cache.json` path
   reference at line 39. Renumber the remaining steps (currently 1,2,3,5,6,7,9 after
   removal) to stay sequential (1-7).
6. In the renumbered "Synthesize the report" step (was Step 7), drop the "Include cached
   (unchanged) verdicts... labeled as cached" language since there's no cache to draw
   from anymore - every matched ticket with signal now always gets a fresh investigation
   per the dispatch-volume gate (was Step 5, now renumber accordingly).
7. If a `state/` directory or `audit_cache.json` file already exists on disk under
   `skills/shortcut-done-audit/`, delete it (it's dead state once the skill stops writing
   to it) - check first with `Glob skills/shortcut-done-audit/state/**` before assuming
   it's empty.

## Acceptance

- `zng-biller` appears in the repo list and in both git loops (fetch step, commit-match
  step) alongside the other three ZNG repos.
- No remaining reference to `audit_cache.json`, `state/`, "dedupe cache," or "cached
  (unchanged)" anywhere in `skills/shortcut-done-audit/SKILL.md` after the edit (grep to
  confirm zero hits).
- Step numbering in the file is sequential and internally consistent after removing the
  two dropped steps (no stale "Step 6" cross-reference pointing at a step that no longer
  holds that content - re-read the file end to end to check every step's own number
  matches what it's referred to as elsewhere in the file, e.g. Step 6's reference to
  "the dispatch-volume gate" and "investigation-prompt.md").

## Notes

- completed, commit 937f802
