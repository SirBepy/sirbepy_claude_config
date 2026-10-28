<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=7, reconfirm-count=1, content-hash=ee707839 -->
<!-- duplicate-checked: 456 is comment-noise.sh flagging generated files (exit 1, already in done/); this is repo-resolution failing on a path deleted from the working tree (exit 2). Different script step, different failure, different fix. -->
# prefilter-gate.sh exits 2 when the pathspec includes a staged deletion

**Type:** skill-improvement
**Origin:** ai

## Goal

`bash ~/.claude/skills/commit/prefilter-gate.sh <files>` should tolerate a path that is staged for deletion, instead of aborting the whole gate with exit 2.

## Context

Hit 2026-09-05 while committing in `C:\Users\tecno\Desktop\Projects\sirbepy_roblox`. The commit deleted `packages/obby-system/assets/README.md` via `git rm` and modified two other files. Running the gate over the commit's own pathspec:

```
bash ~/.claude/skills/commit/prefilter-gate.sh \
  packages/obby-system/default.project.json \
  packages/obby-system/wally.toml \
  packages/obby-system/assets/README.md
ERROR: could not find a git repository for packages/obby-system/assets/README.md
gate exit=2
```

The file is gone from the working tree (correctly - it is a deletion), so the gate's repo-resolution step fails on it and takes the whole invocation down with exit 2, even though the other two paths are fine.

This matters because `commit/SKILL.md` step 8 mandates chaining the gate to the commit: `prefilter-gate.sh <files> && git commit -m "..." -- <files>`. With a deletion in the pathspec that chain can never fire, so the operator has to drop the deleted path from the gate call by hand and run the two commands separately - which is exactly the "commit landed before the flagged output was read" gap todo 356 closed.

Exit 2 is documented as "the gate itself could not run, fix the path/cwd and rerun", but here there is nothing to fix: the path is legitimately absent by design.

## Approach

In `skills/commit/prefilter-gate.sh`, before resolving a path's repo, check whether it exists in the working tree. If it does not, verify it is staged for deletion (`git diff --cached --name-status -- <path>` returning `D`) and skip it silently - a deleted file has no added lines, so em-dash, comment-tense and secret scans have nothing to inspect. Only a path that is both missing from disk AND not a staged deletion should still produce exit 2.

Rejected: making the caller strip deleted paths. That pushes a mechanical rule onto every operator and re-opens the chaining gap the gate exists to close.

## Acceptance

- The three-path invocation above exits 0 and scans the two surviving files.
- A genuinely bogus path (never tracked, not on disk) still exits 2 with the same plain-English `ERROR:` line.
- A pathspec of only deleted files exits 0 rather than 2.
- `python ci/run_all.py` still passes.

## Notes

- DONE 2026-09-10 via /loop-todos cycle 1, in two passes, and the second one matters. The builder handled the STAGED deletion shape: skills/commit/prefilter-gate.sh:34-72 now walks up to the nearest surviving ancestor directory when a path is missing from disk (a staged removal can take the last file AND its directory), resolves a repo from there, and asks the INDEX rather than the working tree whether that exact path is legitimately gone. Verified against the real gate immediately after, the orchestrator found the fix did not cover the shape that actually filed this todo: complete-todo.ps1 archives with Move-Item and only git-adds the destination, so the source deletion sits UNSTAGED, where git diff --cached reports nothing and the path still exits 2. Both deletions are now handled, and they need DIFFERENT questions, which is the real lesson: a staged removal drops the path from the index so ls-files misses it while diff --cached reports D, whereas an unstaged deletion leaves the path in the index so ls-files finds it while diff --cached is silent. The gate asks both and only exits 2 when neither recognises the path, which is what keeps a typo or a wrong cwd a real error. Four cases in skills/commit/test_prefilters.sh cover staged-alone, staged-mixed-with-a-live-file (proving the scan is not blinded), the new unstaged case, and the never-tracked path. Proven on this repo live tree, not just fixtures: the gate now exits 0 on a real archive pathspec that previously forced hand-filtering. python ci/run_all.py exits 0.
