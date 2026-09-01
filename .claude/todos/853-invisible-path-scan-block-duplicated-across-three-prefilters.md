<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=EASY, worth=5, reconfirm-count=1, content-hash=482b3238 -->
<!-- duplicate-checked -->
<!-- Grepped .claude/todos/ and done/ for prefilter helper / invisible path / secret-scan port: done/804 and done/460 are the parents, no live match. -->
# The invisible-path scan block now exists three times across the commit prefilters

**Type:** skill-improvement
**Origin:** ai

## Goal

Collapse the roughly 15-line "gitignored or otherwise invisible path, scanned via
`git diff --no-index`" block into one shared source, so a future fix to that behaviour is one edit
rather than three synchronized ones.

## Context

Filed 2026-08-31 by an independent `/code-check` reviewer over a `/mega-todos` run's whole diff.

Todo `460` originally fixed this blind spot in `skills/commit/secret-scan.sh`. Todo `804` then ported
the same block verbatim into `skills/commit/comment-noise.sh` and `skills/commit/em-dash.sh`. There
are now three byte-identical copies of the logic:

- `skills/commit/secret-scan.sh:78-81,101-110` (the original)
- `skills/commit/comment-noise.sh:60-63,83-93`
- `skills/commit/em-dash.sh:49-52,72-81`

All three run the same `git ls-files --error-unmatch` check, then the same
`git ls-files --others --exclude-standard` check, then route anything in neither set through
`git diff --no-index -- /dev/null <f>`, with the same `ERROR:` message format.

**`804`'s builder considered a shared helper and deliberately chose not to build one**, reasoning
that the repo already tolerates this same untracked-files loop duplicated three times as a
pre-existing convention, and that sourcing an array-returning helper across a shell boundary adds a
new quoting surface. That reasoning is on record and is not obviously wrong. This todo is the
reviewer disagreeing with it, not a discovered defect: the argument against is that `460`'s own bug
class is exactly the kind that recurs, and next time it will need three synchronized edits with no
single source of truth.

Decide it once, either way, and write the decision down so it stops being re-litigated per todo.

## Approach

1. Read `done/804-comment-noise-shares-secret-scans-gitignored-blind-spot.md`'s Notes for the
   builder's reasoning, and `done/460-prefilters-report-clean-on-a-gitignored-file.md` for the
   original bug, before deciding anything.
2. If extracting: create `skills/commit/_prefilter-lib.sh` with a `scan_invisible_paths` helper and
   have all three scripts source it. Watch the array-passing quoting carefully; that is the specific
   risk `804`'s builder named.
3. If NOT extracting: write the decision and its reasoning into `skills/commit/comment-noise.md` or
   a sibling doc, so the next reviewer finds the answer instead of re-filing this.
4. Either way, verify by reproducing `460`'s original bug against all three scripts afterwards: a
   genuinely gitignored file with a planted hit must still be reported by each.

## Acceptance

- [ ] A decision exists in writing, extract or do-not-extract, with the reasoning
- [ ] If extracted, all three scripts share one implementation and none has a stale copy
- [ ] A gitignored file with a planted hit is still reported by all three scripts
- [ ] The pre-existing carve-outs still apply: `.md`/`.mdx` skip in comment-noise.sh, and the
      `.claude/todos/` exempt-marker logic in em-dash.sh
- [ ] `python ci/run_all.py` exits 0, noting explicitly that it does not cover these three scripts

## Notes

- Worth roughly a 5. Real duplication with a real recurrence argument, but the reviewer's case is a
  prediction and the builder's counter-case is a measured quoting risk. The value here is settling
  it, not the extraction itself.
- None of the three scripts has a test file, which is why the acceptance leans on manual
  reproduction rather than a suite.
