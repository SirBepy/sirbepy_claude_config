<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# flutter-bump: resolve the 2c-step-4 vs section-3 workspace-write contradiction (Joe picks)

**Type:** skill-improvement

## Goal

`skills/flutter-bump/SKILL.md` has two places that write `dart.flutterSdkPath` into the
shared `zng-admin.code-workspace` file, with contradictory gating: 2c step 4 writes it
PER-REPO, unconditionally, DURING the sequential repo loop (before knowing whether all
three repos will end up on the same version); Section 3 writes the SAME value again
AFTER the loop, but ONLY if all three repos landed on the exact same version. If repo 1
bumps successfully and repo 2 or 3 then fails/skips, 2c step 4 has already written repo
1's version into the shared workspace file - directly contradicting Section 3's explicit
guard against exactly that outcome. Resolve by either deleting 2c step 4 (let Section 3's
gated write be the only one) or dropping Section 3's all-three gate (accept that the
workspace file follows whichever repo bumped last) - **Joe picks which.**

## Context

`skills/flutter-bump/SKILL.md` (as of 2026-08-01):

**2c step 4** (lines 83-88), inside the per-repo "Bump" sub-steps, runs for EVERY repo,
every time it bumps, with no cross-repo agreement check:
```
4. Also add/update `dart.flutterSdkPath` in `zng-admin.code-workspace`'s
   top-level `settings` block (`C:\Users\tecno\Desktop\Projects\zng-admin.code-workspace`)
   to the same absolute path â€” see step 3 of the new "Multi-root workspace
   file" section below. Both need to happen together: the per-folder value
   for when a repo is opened standalone, the workspace-level value as the
   belt-and-suspenders fix for when it's opened via the bundled workspace.
```

**Section 3, "Multi-root workspace file"** (lines 145-178), runs ONCE after the entire
3-repo loop completes, explicitly gated:
```
Fix: after the repo loop, only if **all three** Flutter repos (zng-app,
zng-admin, zng-biller) ended up on the exact same final version (freshly
bumped or already-on-target â€” never a skipped/failed one), set or update an
explicit workspace-level SDK path so the shared server has no ambiguity to
fall back from:
...
If the three repos are NOT all on the same version (one was skipped or
failed verify), leave the workspace file untouched and say so explicitly in
the final report â€” forcing the new version here would break analysis for
whichever repo didn't move.
```

These two write the SAME setting in the SAME file with OPPOSITE gating philosophies. As
written today, running the skill against a scenario where zng-app bumps to version X
successfully but zng-admin then fails its `git pull --ff-only` (per 2a's documented skip
condition) would: write X into the workspace file during zng-app's own 2c-step-4 (no
gate), then Section 3 would correctly detect the 3 repos are NOT all on the same version
and explicitly declare it will "leave the workspace file untouched" - except it's already
been touched, by step 4, contradicting Section 3's own stated guarantee and its final
report's truthfulness ("forcing the new version here would break analysis for whichever
repo didn't move" - but step 4 already forced it, unconditionally, for zng-app alone).

## Approach

**Do not silently pick one option - this explicitly needs Joe's call per the original
audit ask.** When picked up:

1. Re-read both sections in full (2c "Bump" sub-steps, lines ~65-104; Section 3 "Multi-root
   workspace file," lines ~145-178) to confirm the contradiction still exists as described
   (the skill may have been edited since 2026-08-01).
2. Surface the two options to Joe via `AskUserQuestion` (domain tag `[ARCH]`, since this
   is a design/data-flow decision about when a shared config file gets touched):
   - **Option 1 - delete 2c step 4.** Only Section 3 writes the workspace file, only when
     all three repos agree. Simpler, matches Section 3's own stated guarantee, but means
     a standalone single-repo bump (if the skill is ever invoked/adapted for just one
     repo) never gets the workspace-level fix even though that repo's own per-folder
     `dart.flutterSdkPath` (2c step 3) still gets the absolute-path fix.
   - **Option 2 - drop Section 3's all-three gate.** Every bump immediately updates the
     shared workspace file to whatever version that repo just landed on, always. Matches
     2c step 4's current unconditional behavior, but means a partial/failed bump run
     (only 1-2 of 3 repos moved) leaves the workspace file pointing at a version that
     doesn't match every repo the workspace bundles - reintroducing exactly the
     analyzer-resolution bug this whole mechanism (documented at lines 145-156,
     Dart-Code's relative-path resolution bug) was built to prevent for whichever repo(s)
     didn't move.
3. Implement whichever option Joe picks. If Option 1: delete 2c step 4 entirely (lines
   83-88) and renumber the remaining 2c sub-steps. If Option 2: delete Section 3's
   "only if all three... ended up on the exact same final version" gate (and the
   corresponding "If the three repos are NOT all on the same version... leave the
   workspace file untouched" fallback), making Section 3's write unconditional -
   though at that point Section 3 becomes redundant with 2c step 4 and could likely be
   merged into it or removed as a separate section entirely (surface this simplification
   to Joe too if Option 2 is chosen).

## Acceptance

- Joe has explicitly chosen Option 1 or Option 2 (not silently defaulted).
- The chosen option is implemented consistently - no remaining trace of the OTHER
  option's gating logic contradicting it.
- Re-read the full file after editing to confirm the "Final report" section (lines
  216-239, specifically the "whether `zng-admin.code-workspace`'s `dart.flutterSdkPath`
  was updated... or left alone because the three repos landed on mismatched versions"
  reporting line) still accurately describes the ACTUAL behavior after the fix, not the
  old contradictory behavior.

## Notes

- Resolved 2026-08-11 in commit 6271b64: 2c's per-repo workspace write deleted, Section 3 is now the only gated writer, so its 'left untouched' claim is literally true on a partial bump. Candidate 2 (unconditional write) was rejected because it leaves the shared file holding whichever repo bumped last.
