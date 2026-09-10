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
