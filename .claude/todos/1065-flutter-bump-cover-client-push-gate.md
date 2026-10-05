<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped the backlog for "flutter-bump". Only hit is 1064, which is about foreign-hunk-check.sh, a different fix. -->
# 1065 - /flutter-bump: cover the client push gate and the steps it keeps missing

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-10-02

## Goal

A `/flutter-bump` run should reach the push without improvising. Today the skill says "commit +
push per repo", but all three ZNG repos are client repos, so `hooks/client-push-gate.py` blocks
every push until /code-check and /e2e have run. The skill does not mention this gate.

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
  suite both phases at `--concurrency=5`; admin/biller smoke), then `_client_repo.py mark`. Joe's
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
