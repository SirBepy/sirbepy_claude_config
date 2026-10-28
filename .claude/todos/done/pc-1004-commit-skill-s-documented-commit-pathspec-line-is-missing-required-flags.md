<!-- Claim before executing: .claude/todos/.claims/1004.claim -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=8, reconfirm-count=1, content-hash=aa8e82a8 -->
<!-- duplicate-checked: 2026-09-24; grepped this backlog for "commit-pathspec" - 985/989/994 all cover the own-range/short-sha REFUSAL behaviour once the script is running. None covers the invocation line in SKILL.md itself being uncallable. done/964 is the todo that created the script. -->
# `/commit`'s documented `commit-pathspec.sh` line is missing required flags

**Type:** skill-improvement
**Origin:** ai

## Goal
The `commit-pathspec.sh` invocation printed in `skills/commit/SKILL.md` step 8 runs as
written, and the `--force` check names it refers to are discoverable from the prose.

## Context
Hit 2026-09-24 in `claude_usage_in_taskbar`. Step 8 documents the script as:

```
bash ~/.claude/skills/commit/commit-pathspec.sh -m "<message>" -- <files>
```

That exits 2 immediately:

```
ERROR: --expect-branch, --expect-sha, -m and -- <files> are all required
```

The script's own header comment (`commit-pathspec.sh:16`) has the real signature -
`--expect-branch <b> --expect-sha <sha>` - and the parser enforces it at `:92`. So the
information exists; the skill prose that tells you to run it does not carry it. The two
values ARE already recorded by step 1a as this run's EXPECTED branch and sha, so nothing
new has to be computed - only the documented line has to name them.

Second, smaller gap in the same step: the prose says a judgement branch "needs an explicit
`--force <check>` naming which one" but never lists the names. `--force overlap-check`,
the obvious guess from the `[overlap-check]` label the script itself prints, is rejected:

```
ERROR: unknown --force check name overlap-check (valid: head-guard, overlap, foreign-hunk, coverage)
```

Neither is a behaviour bug - both are one wasted round trip each, on the FIRST script call
of a session, before any of the guards have run. Cost measured here: 2 extra invocations
before the first commit landed.

Distinct from the existing three: 985 and 989 are about `foreign-hunk-check` refusing as
UNVERIFIED and then printing the ranges it refused for; 994 is about `--expect-sha`
rejecting a 7-char sha. All three are about a call that reached the guards. This one never
gets that far.

## Approach
Both fixes are in `skills/commit/SKILL.md` step 8, no script change needed:

1. Change the documented invocation to the real signature, threading step 1a's own recorded
   values so the reader sees where they come from:
   `bash ~/.claude/skills/commit/commit-pathspec.sh --expect-branch <step 1a's EXPECTED branch> --expect-sha <step 1a's EXPECTED sha> -m "<message>" -- <files>`
2. In the same paragraph, name the four valid `--force` values inline
   (`head-guard`, `overlap`, `foreign-hunk`, `coverage`) and note they do NOT match the
   bracketed labels the script prints (`[overlap-check]` is forced with `overlap`).

## Acceptance
- Copying the invocation line out of SKILL.md verbatim, substituting only the four
  placeholders, runs the full chain rather than exiting 2.
- The `--force` names appear in SKILL.md, so no read of the script is needed to use it.

## Notes
- 2026-09-29, hit again in `~/.claude`: both gaps above cost a round trip each, plus a third one.
  Passing `--force overlap --force foreign-hunk` as two flags silently keeps only the LAST one
  (`commit-pathspec.sh:84` overwrites `force_list` on each `--force`), so the overlap refusal fired
  again. Only the comma form `--force overlap,foreign-hunk` works. Document the comma form in step 8
  alongside the names, or make the parser append instead of overwrite.
- 2026-10-01, hit again from a zng-app session: copied step 8's documented line
  (`commit-pathspec.sh -m ... -- <files>`), got `ERROR: --expect-branch, --expect-sha, -m and -- <files>
  are all required`, one extra round trip. Still unfixed in SKILL.md as of that date.
- Completed by /loop-todos cycle 1 (2026-10-05). Script halves: eccffe6, 5d6f7b2, 61e7fae, f582722 (tests in skills/commit/test_*.sh); doc halves in skills/commit/SKILL.md (this commit) and e9f4620.
