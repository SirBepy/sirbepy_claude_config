<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# `comment-noise.sh` flags generated files, so `prefilter-gate.sh` cannot exit 0 on a codegen commit

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `skills/commit/comment-noise.sh` skip machine-generated files, so `prefilter-gate.sh`'s exit
code stays a usable gate on any commit that includes codegen output.

## Context

Filed 2026-08-20 from a revaire-mobile session (`REV-4810`, travel plans feature commit).

`/commit` step 8 tells the session to chain `prefilter-gate.sh <files> && git commit ...` precisely
so a flagged diff structurally cannot reach the commit. That chain is only meaningful if a clean
diff can actually produce exit 0.

In this commit it could not. The gate returned exit 1 on:

```
lib/models/feature_flag/feature_flag.freezed.dart 93/280 (33%) longest 12
lib/models/travel_plan/travel_plan_draft.freezed.dart 94/292 (32%) longest 12
lib/models/travel_plan/travel_plan_leg_draft.freezed.dart 93/292 (31%) longest 12
```

Every hand-written file in the same 57-file commit passed. These three are `build_runner` output
from `@freezed`, and that repo's own rules (`.claude/rules/dart-state.md`) say "Never edit `.g.dart`
or `.freezed.dart` files" - the flagged comments are literally unfixable, since the next codegen run
reverts any trim. The prescribed treatment ("trim the offending blocks now, don't ask") has no valid
action here.

So the session had to break the `&&` chain and run the gate on a hand-written subset to get a
truthful exit 0. That is exactly the gap todo 356 closed for a different reason, reopened by a false
positive.

**Not a duplicate of done/258** (pure code moves). That one is about comments that are real
documentation which merely LOOK new because a move shows them as added lines, and it was resolved
with a judge step: confirm via `git show HEAD:<old-file>`, then keep them. This one has no judge
step available - the file is not authored by anyone, and the correct action is "never look at it",
not "look, then decide". Also not done/249 (pipeline/chaining mechanics) or 447 (cross-repo target).

**Scope is not one repo.** `comment-noise.sh` already carries a language-aware carve-out for
markdown headings (`if (f ~ /\.(md|mdx)$/) next`, todo 340), so the precedent for filtering by
filename exists. Generated files are broader than Dart: `*.pb.go`, `*_pb2.py`, `*.g.dart`,
`*.freezed.dart`, `*.generated.*`, and anything under a `generated/` directory hit the same wall.
Any repo that commits codegen output - revaire-mobile does, deliberately - trips this on every model
change.

## Approach

1. Add a generated-file skip to the awk program in `skills/commit/comment-noise.sh`, in the same
   place and style as the existing markdown carve-out. Candidate match set, to be confirmed rather
   than assumed: `\.(g|freezed)\.dart$`, `\.pb\.go$`, `_pb2\.pyi?$`, `\.generated\.[a-z]+$`,
   `(^|/)generated/`.
2. Decide whether the same skip belongs in `em-dash.sh`. Probably yes for the identical reason (a
   generated file's em dashes are not authored and cannot be fixed), but check first whether any
   generator this dev uses actually emits one - if none does, adding it is speculative and should be
   left out.
3. Do NOT solve this by teaching `/commit` to pass a filtered file list. The caller should be able to
   hand the gate the real commit pathspec; moving the filter into every call site is how the
   filename-quoting bug the `-z` comment documents got in.

## Acceptance

- `bash skills/commit/comment-noise.sh` run against a real diff containing a `.freezed.dart` (or an
  equivalent generated file) prints nothing for that file, and still prints for a hand-written file
  in the same diff that genuinely breaches the cap. Paste both runs' actual output.
- `bash skills/commit/prefilter-gate.sh <that same file list>` exits 0, shown with `echo $?`.
- `python ci/run_all.py` still exits 0.

## Notes

Do not widen this into "generated files are exempt from all checks". `secret-scan.sh` must keep
reading them - a credential baked into a generated config is still a real leak, and it is the one
prefilter whose hits are never auto-resolved.
