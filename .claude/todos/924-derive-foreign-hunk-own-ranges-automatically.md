<!-- duplicate-checked: 806 (done/) shipped foreign-hunk-check.sh itself, the COMPARISON half. This is the residual gap in what it shipped - the script takes `--own` line ranges as an argument, so the caller still hand-derives them, which is the "stop being a per-file manual read" half of 806's own Goal that did not land. 474 (done/) is the sibling overlap-check script and takes shas, which are recallable; only the line-range variant has this problem. 290 is the em-dash prefilter, different script. -->
<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# foreign-hunk-check still makes the caller hand-derive its --own line ranges

**Type:** skill-improvement
**Origin:** ai

## Goal

Finish what todo 806 started: running `/commit` step 8's working-tree diff
check should not require anyone to read a `@@` header.

## Context

806 shipped `skills/commit/foreign-hunk-check.sh` (commit `49fd7a2`) and closed.
It delivered the comparison, but its interface takes the caller's own line
ranges as an argument:

```
foreign-hunk-check.sh -C <repo> --own <file>:<a>-<b>[,<a>-<b>...] <files>
```

806's Goal was for this to "stop being a per-file manual read", and its Approach
assumed "the harness knows which files/edits this session made". The shipped
script does not derive that, so `/commit` step 8 says the ranges are "recalled
the same way step 1a's own-commit list already is" - and a model cannot recall
exact line numbers after a session of edits.

What actually happens, done twice on 2026-09-04 in claude_usage_in_taskbar
across two `/commit` invocations in one session:

1. `git diff -U0 -- <files> | grep -E '^\+\+\+|^@@'`
2. read each `@@ -old +new,count @@` header
3. hand-convert `+N,M` to `N-(N+M-1)`, and a bare `+N` to `N-N`
4. paste the result back as `--own`

Steps 2 and 3 are transcription with a silent failure mode: a wrong range makes
the check report `clean` while genuinely foreign hunks ride along, which is the
exact outcome the gate exists to prevent. Nothing verifies the transcription.

Not the same problem as `overlap-check.sh` (todo 474, also done): that one takes
shas, which the model genuinely does hold in context. Only the line-range
variant is unrecallable.

## Approach

1. Teach `foreign-hunk-check.sh` to derive the current working-tree hunk ranges
   itself from `git diff -U0`, which is the same parse it already performs one
   step later. The caller then declares only what it did NOT write, or nothing
   at all in the common single-session case.
2. If `--own` must stay the interface for compatibility, ship a sibling that
   prints a ready-to-paste `--own` argument for a pathspec, and have step 8 call
   that rather than describing the manual recipe in prose.
3. Update `skills/commit/SKILL.md` step 8 to call whichever lands, and drop the
   "recalled the same way" wording, which asks for something unreliable.

Rejected: "be more careful when reading the diff". The gate exists precisely
because eyeballing a shared checkout is unreliable, so a manual transcription
step inside it is self-defeating.

## Acceptance

- `/commit` step 8 runs without the caller reading a single `@@` header.
- A missing range no longer silently passes: dirty a file with two separate
  hunks, declare only one, and confirm the other is still reported.
- The existing exit-code contract (0 clean, 1 foreign hunks, 2 could not run)
  is unchanged, and 806's sub-hunk case
  (`foreign-hunks-inside-your-hunk`) still fires.

## Notes

- Surfaced 2026-09-04 during `/close` in claude_usage_in_taskbar, a repo that
  routinely runs several Conductor sessions against one checkout, which is the
  same setting that produced 806.
- Related: [[806-shared-worktree-foreign-hunk-check-helper]] (done, shipped the
  script), [[474-commit-step-8s-overlap-check-should-be-a-script]] (done, the
  sha-based sibling).
