<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped for stale-bundle/build-before-commit/assertBundleIsNotStale, only hit was unrelated done/803 -->
# 1177 - flutter-bump's step order trips zng-app's own stale-bundle e2e guard

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop `/flutter-bump` from reliably failing zng-app's first e2e attempt on every run, by fixing the
step order rather than relying on a manual rebuild-and-retry each time.

## Context

`~/.claude/skills/flutter-bump/SKILL.md` section 2's per-repo loop runs 2d (verify: analyze, test,
`build web`, then the local-defines rebuild) BEFORE 2e (commit the bump files, then the push gate's
`/code-check` + `/e2e`). zng-app's own `e2e/lib/server.js:77` (`assertBundleIsNotStale`) refuses to
drive a `build/web` bundle whose mtime predates `HEAD`'s commit time. Because 2d's build always
happens before 2e's commit, by construction `build/web`'s mtime is always older than the commit the
push gate's `/e2e` step then checks against - the guard fires on the FIRST attempt every single
time, not just occasionally.

Reproduced 2026-10-13 bumping zng-app 3.47.6 -> 3.47.7: `run-all.js --target=local --concurrency=5`
crashed immediately with `run-all crashed: Error: build/web was built <T1> but HEAD was committed
<T2>, so the suite would drive a bundle missing the code under test` where T1 < T2 as predicted.
Worked around in the moment by rebuilding `build/web` (release, `--dart-define-from-file=.env.local`)
after the commit landed, re-verifying `flutterRoot` and the bundle's API target, then re-running the
suite - which then passed (15/17, 2 flaky flows that both passed clean on an isolated retry).

## Approach

Move (or duplicate) the local-defines rebuild (2d step 4) to run AFTER 2e step 1's commit, immediately
before 2e step 2's `/e2e` call - or have the push gate's `/e2e` step rebuild for itself right before
running. Either way the invariant needed is: whatever `build/web` the suite drives must have an mtime
newer than the commit it's gated on. Re-verify `flutterRoot` (2c step 4 / 2d's existing re-check) after
whichever rebuild ends up last, same as today.

## Acceptance

- Running `/flutter-bump` against zng-app no longer hits `assertBundleIsNotStale` on the first e2e
  attempt purely because of step ordering (a genuinely stale build from an unrelated cause is still
  fine to catch).
- The skill's own section 2d/2e text reflects the corrected order so a cold run doesn't rediscover
  this by hitting the crash again.

## Notes

- Completed 2026-10-23 (loop-todos cycle 1): local-defines rebuild moved to 2e step 2 (after the commit, before the push gate) with the flutterRoot re-check after it, so build/web is newer than HEAD for assertBundleIsNotStale (zng-app e2e/lib/server.js:56-83). Not exercised in a real bump.
