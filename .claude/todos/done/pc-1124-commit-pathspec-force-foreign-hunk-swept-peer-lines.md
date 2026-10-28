<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=HARD, worth=8, reconfirm-count=1, content-hash=e3298a08 -->
<!-- duplicate-checked: 1119 is the session's OWN parallel builders under one marker; this is a PEER session's hunks swept by an explicit --force foreign-hunk override with 2+ markers, the case 924/933 refuse by default -->
# commit-pathspec's --force foreign-hunk took a peer session's in-progress lines with no warning

**Type:** skill-improvement
**Origin:** ai

## Goal

Overriding the foreign-hunk refusal can't silently commit a concurrent session's in-progress
hunks. Before the commit lands, the caller sees which hunks it is taking that it did not write.

## Context

2026-10-07, mc_plugins_tag, session 62d7. `commit-pathspec.sh` correctly refused with
`[foreign-hunk-check] UNVERIFIED` (several live session markers). Claude passed
`--force foreign-hunk`, reasoning that every hunk in the pathspec was its own, and committed
72c727b with `server/resourcepacks/claudesmp-items/README.md` and
`server/resourcepacks/test_build_server_pack.py` taken whole. A peer session (00ba, phantom buff)
had in-progress hunks in both: a new README "## Phantom sounds" section, and a rewritten test that
replaced `test_vanilla_sounds_are_untouched`. Those landed under Claude's commit, while the peer's
`sounds.json` and listener did not. HEAD's pack test then failed until the peer committed its
remaining files. Claude caught it only because the harness said "changed on disk since you last
read it" after the commit. Nothing was lost, but the history mixes two features.

The `--force` flag is one token, and the script prints nothing about what it is about to take.

## Approach

Edit `skills/commit/commit-pathspec.sh` (and the `/commit` SKILL.md step 8 prose that documents
`--force foreign-hunk`). When `--force foreign-hunk` is given and 2+ live markers exist, print
every hunk header per file (`file: @@ -a,b +c,d @@` plus the first changed line) before
committing. Better still, refuse `--force foreign-hunk` unless `--own-range` is also given for
each multi-hunk file, so the override needs a stated claim rather than a bare flag. Add a hooks
self-test that builds a two-session scenario and asserts the hunk list is printed or the
commit refused.

## Acceptance

- Re-running the 2026-10-07 shape (a file with one own hunk and one peer hunk, 2 live markers,
  `--force foreign-hunk`) either refuses or prints both hunks before committing.
- `python ci/run_all.py` passes in `~/.claude`.

## Notes

- --force foreign-hunk with 2+ live markers now refuses a file with 2+ auto-derived hunks and no --own-range, and prints the single hunk it takes on trust otherwise; RED reproduced the 2026-10-07 silent sweep, GREEN refuses. SKILL.md step 8 documents it. Full test_commit_pathspec.sh and ci/run_all.py passed.
