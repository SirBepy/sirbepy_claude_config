<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=HARD, worth=6, reconfirm-count=4, content-hash=4d6cdf85 -->
<!-- duplicate-checked: grepped the backlog for "flutter-bump". Only hit is 1064, which is about foreign-hunk-check.sh, a different fix. -->
# 1065 - /flutter-bump: cover the client push gate and the steps it keeps missing

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-10-02
**Summary:** A /flutter-bump run reaches the push without improvising, because the skill covers the push gate and the steps it keeps missing.

## Why

On the 2026-10-02 bump from 3.47.5 to 3.47.6 all three pushes were denied by the push gate, which the skill never mentions, and the run needed a hand-written smoke test.

## Goal

A `/flutter-bump` run should reach the push without improvising. Today the skill says "commit +
push per repo", but `hooks/push-gate.py` (renamed from `client-push-gate.py` 2026-10-05, now
gating every repo) blocks every push until /code-check and /e2e have run. The skill does not
mention this gate.

## Context

Seen on the 2026-10-02 bump from 3.47.5 to 3.47.6, in a zng-app session:

1. **The push gate.** All three pushes were denied. Joe chose "run e2e, /test all 3, push only
   if green". zng-admin and zng-biller have no e2e suite, so Claude hand-wrote a throwaway
   Playwright smoke script (`c:\tmp\zng-smoke.cjs`): serve a release build, log in through
   `auth/login` + `auth/verify` 000000, seed localStorage, click the left nav, assert routes and
   that there are no page errors. The project memory
   `reference_admin_biller_local_smoke_e2e.md` (zng-app auto-memory) has the full recipe, accounts
   and coordinates.
2. **The local backend was down.** `zng-api:start-clean` had to be started
   (`sv.ps1 ensure ... -NoDynamicPort`, about 3 minutes to a healthy `/health`), and docker
   `postgres`, `localstack` and `sftp-server` were `Exited (255)`.
3. **flutterRoot reverted mid-run.** After zng-app's local-defines rebuild,
   `.dart_tool/package_config.json` and `.dart_tool/version` showed 3.47.5, written at the second
   the build finished. `fvm flutter --version` and every `fvm flutter` call resolved 3.47.6, so the
   writer was a process outside the session. UNVERIFIED: probably a VS Code window on the old SDK
   (the multi-root workspace case in the skill's section 3). `fvm flutter pub get` repaired it, and
   a second build kept 3.47.6. The skill's 2c step 4 checks flutterRoot only after `fvm use`, not
   after the zng-app local-defines rebuild in 2d step 4.
4. **Smaller snags.** `commit-pathspec.sh` needs `--expect-branch` and `--expect-sha`, which the
   skill's pathspec-commit line does not show. `push-read-gate.py` requires
   `snippets/auto-commit.md` to be read before the first push. zng-app's `build/` cannot be read
   by the main session's tools, so the `grep -c localhost:3009` check in 2d step 4 has to go
   through `node -e` instead.

## Approach

In `skills/flutter-bump/SKILL.md`:

- Add a push-gate step between 2e's commit and push: /code-check on the bump commit, /e2e (zng-app
  suite both phases at `--concurrency=5`; admin/biller smoke), then `push-gate.py mark`. Joe's
  2026-10-02 call is the policy to encode: push only if all are green.
- Promote the admin/biller smoke into a committed helper, for example
  `skills/flutter-bump/scripts/smoke.cjs` taking repo, email and nav JSON. Keep the accounts and
  coordinates in a references file, since they drift (the zng-biller nav moved between 2026-09 and
  2026-10).
- Add a "start local zng-api + docker deps" preamble, or point at the existing memories for it.
- Re-check flutterRoot after the 2d step 4 rebuild, not only after `fvm use`.
- Replace the `grep -c` in 2d step 4 with the `node -e` form, and show the full
  `commit-pathspec.sh` invocation.

## Acceptance

- A cold session runs `/flutter-bump` through to pushed commits in all three repos without
  improvising a script or rediscovering the gate.
- The smoke helper exists in the skill folder and runs against local zng-api for admin and biller.

## Notes

- /loop-todos 2026-10-05: step 2e now runs the push gate via skills/commit/SKILL.md's Push pipeline, plus the backend precondition, flutterRoot re-check and full commit-pathspec invocation. Still open: the committed admin/biller smoke helper (skills/flutter-bump/scripts/smoke.cjs); its recipe and accounts live in zng-app's project memory (reference_admin_biller_local_smoke_e2e.md), so build it from a zng-app session against a live local backend.

- 3.47.9 bump, 2026-11-03: a likely writer for the flutterRoot reversion in finding 3. zng-app's `package_config.json` went back to 3.47.8 between the local-defines rebuild and the final check, with no message from a peer. A `bash /c/Users/tecno/fvm/default/bin/flutter analyze --no-fatal-infos` run was live on 3.47.8, because `fvm\default` keeps the old version until the skill's final `fvm global` step. That command is allowlisted in zng-app's `.claude/settings.local.json`, so it is probably a peer chat; its cwd and the exact write were not confirmed. `fvm flutter pub get` repaired it after `fvm global`, and it held. Consider running `fvm global` right after `fvm install`, and re-reading flutterRoot in all three repos in the final report.

## Answers 2026-10-08

- Joe, 2026-10-08 (todo-questions chat): build the smoke helper at the next Flutter bump, when zng-api is running anyway. Not before.

## Notes (2026-10-13 bump, 3.47.6 -> 3.47.7)

This WAS "the next Flutter bump" Joe meant, and the committed helper still did not get built: this
todo wasn't re-read until a `/close` pass after all three repos were already bumped and pushed, so
the smoke check was hand-written again as two more throwaway scripts instead
(`zng-admin/.for_bepy/flutterbump-smoke.cjs`, `zng-biller/.for_bepy/flutterbump-smoke.cjs`, both
confirmed PASS against local zng-api on :3009, same recipe as before). Per CLAUDE.md, editing the
actual skill file/scripts is not something a project session does unprompted, so this still needs a
dedicated `~/.claude` session to: (1) generalize the two scripts above into
`skills/flutter-bump/scripts/smoke.cjs` (repo, email, nav-JSON params), (2) put the accounts/coords
in a references file, (3) wire 2e to call it instead of hand-writing one. The two 2026-10-13 scripts
are a closer-to-final reference than the 2026-10-02 one (`c:\tmp\zng-smoke.cjs`, since deleted) -
use them as the base.

## Notes (2026-10-29 bump, 3.47.7 -> 3.47.8)

Run from a zng-app session. Two more snags the skill's 2e does not cover, plus a status update:

- `commit-pathspec.sh` refuses the bump commit with `[foreign-hunk-check] UNVERIFIED` whenever 2+
  session markers are live (3 were), so 2e step 1 needs `--own-range .fvmrc:1-3 --own-range
  .vscode/settings.json:1-9999 --own-range flutter.version:1-1` in its example command.
- In zng-biller other files were staged by someone else (`CLAUDE.md`, `pubspec.yaml`,
  `pubspec.lock`), so `[coverage-check]` refused as a possible half-committed move. `--force
  coverage` was the correct answer (those files are not part of the bump). The skill should say so.
- The throwaway `zng-biller/.for_bepy/flutterbump-smoke.cjs` still works unchanged on 3.47.8, so the
  committed `scripts/smoke.cjs` is still unbuilt. zng-admin no longer needs it: it has its own
  `e2e/run-all.js` (6 flows), so the admin half of this todo is obsolete.
- zng-biller's `.env.local` was invalid JSON that run, so the smoke build used inline
  `--dart-define`s; a committed helper should accept that fallback.
