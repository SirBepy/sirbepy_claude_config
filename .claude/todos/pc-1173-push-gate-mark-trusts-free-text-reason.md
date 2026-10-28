<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1065 is about flutter-bump covering the client push gate, not mark evidence (2026-10-13) -->
# 1173 - push-gate `mark` accepts any reason, so /test and /e2e can be skipped as skills

**Type:** skill-improvement
**Origin:** ai

## Goal
Make `hooks/push-gate.py mark` refuse, or at least warn, unless this session's transcript shows the `/test` skill and the `/e2e` skill (plus `/flutter-e2e` when `/e2e` routes there) were actually loaded since the last push.

## Context
On 2026-10-13, in a zng-biller session (sc-56212/56308/56313/56302 push), Claude:
- ran `flutter analyze` and `flutter test` by hand instead of loading `/test`
- loaded `/e2e`, but skipped its "delegate to `/flutter-e2e`" row and hand-wrote a Playwright script without reading `refs/flutter-web-playwright.md`
- then ran `push-gate.py mark --reason "code-check passed ... e2e: ..."` and pushed.

Joe asked "and you definitely did /code-check /test and /e2e?" and the honest answer was no. The gate only checks that `mark` ran for HEAD; the reason is free text that Claude writes itself. `/commit`'s Push pipeline says "/test" and "/e2e" by name, but nothing checks that.

## Approach
In `hooks/push-gate.py`'s `mark` path, read the session transcript the way `hooks/push-read-gate.py` and `hooks/outbound-verify-guard.py` already do. Look for `Skill` tool calls naming `test` and `e2e` after the previous successful `git push` in this session. If `e2e` resolved to a Flutter repo (a `pubspec.yaml` with flutter), also look for `flutter-e2e`. If one is missing, refuse `mark` and name the missing skill. Keep an explicit escape such as `--reason "... e2e: no suite"`, which `/commit` already documents for repos with no suite.

## Acceptance
- A session that never loaded `/test` gets `mark` refused, with the skill named.
- A session that loaded `/test`, `/e2e` and `/flutter-e2e` gets `mark` accepted.
- The existing no-suite path still works.

<!-- loop-skip: dev deferred 2026-10-24 -->
## Deferred questions

Written by /auto-do-todos on 2026-10-23. Deferred by /loop-todos on 2026-10-24: Jarvis (answering for Joe while he was asleep) picked "you decide"; Claude's 2026-10-24 re-check of the real write target found the fix needs a `hooks/` or `settings.json` write, which prompts for permission, so it waits for an attended session.

- [ ] [TOOLING] Run this todo in an attended session (say which). Its fix writes to `hooks/` or `settings.json`, which `hooks/sensitive-file-guard.py` gates with a permission ask, and the autopilot rules bar a dispatched subagent from those writes, so an unattended loop cannot land it.
