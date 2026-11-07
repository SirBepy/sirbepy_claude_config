<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 1065 is about flutter-bump covering the client push gate, not mark evidence (2026-10-13) -->
# 1173 - push-gate `mark` accepts any reason, so /test and /e2e can be skipped as skills

**Type:** skill-improvement
**Origin:** ai
**Summary:** The push gate refuses to mark a push as cleared unless this session actually loaded the /test and /e2e skills since the last push.

## Why

On 2026-10-13 Claude ran the checks by hand, skipped the skills, wrote its own reason text and pushed; Joe asked if it had really run them and the honest answer was no.

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

## Decided

- `mark` finds the session transcript from `CLAUDE_CODE_SESSION_ID` (glob `~/.claude*/projects/*/<id>.jsonl`); `push-read-gate.py` has no transcript reader to copy, the hook payload path is not available to a CLI call.
- "Since the last push" = after the last `git push` whose tool result was not an error or a push-hook refusal, so a denied push does not erase the skills loaded for it.
- A gate chat (first prompt names the Push pipeline from step 2) is not asked for `/test`: its commit-time `/test` ran in the parent chat and the gate runs the CI unit tests itself. `/e2e` is still required there.
- A repo with no fast-check stack (`detect_stack` empty, e.g. the Obsidian vault) needs no skills, so the vault mark in `snippets/auto-commit.md` keeps working.
- Escapes: `e2e: no suite` in the reason waives `/e2e` and `/flutter-e2e`; `--skip-skill-check "<approval>"` covers pushing past a red or impossible check and is recorded in the marker. A transcript that cannot be found or read warns and still marks, since blocking pushes made outside a Claude session is worse than an unverified mark.
- Not done: `/code-check` load is not checked (the todo names `/test` and `/e2e` only).

## Notes

- Deferred question (needs an attended session for its `hooks/`/`settings.json` writes) answered 2026-11-07: Joe said run it now, in the attended 2026-11-07 session; he approves each permission prompt as it appears.
