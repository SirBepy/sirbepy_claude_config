<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 2026-10-08; the original fix is commit 1f9eb1d (todo 1063, done); no live todo covers the 4.5.0 engine -->
# impeccable 4.5.0 replaced the locally patched stop hook; check it does not re-flag known findings every turn

**Type:** task
**Origin:** ai

## Goal
Confirm whether impeccable's new native engine hook repeats the old bug (re-flagging pre-existing
findings on every turn), and re-apply a fix or report it upstream if it does.

## Context
Commit 1f9eb1d (todo 1063) patched `skills/impeccable/scripts/hook-lib.mjs` so the Stop hook stopped
re-flagging known findings every turn, with `hook-lib.test.mjs` and `tools/test_impeccable_hook_lib.py`
covering it. On 2026-10-08 (loop-todos cycle 1, todo 1037) `npx impeccable update` moved the skill to
v4.5.0: the JS hook scripts are gone, and the hooks now run a signed native binary
(`scripts/bin/windows-x64/impeccable.exe hook`, wired by the installer into the gitignored
`settings.local.json`). The local patch and its test no longer exist; the Python wrapper was deleted
because it only checked a file that is gone. Nobody has checked whether upstream fixed the same bug.
The same update also overwrote commit 540c946's local edits to `reference/new-work.md` (scoping
code-check by language, SRI hash pins); `skills/VENDORED.md` now records both as lost. Check whether
4.5.0's `new-work.md` still needs them. Also: the tracked `settings.json` still has two impeccable hook entries pointing at the deleted
`scripts/hook.mjs`; they no-op (`[ ! -f ... ] ||`) and can be removed.

## Approach
1. In a frontend repo, edit a UI file with a pre-existing finding across two or three turns and
   watch whether the Stop hook reports the same finding each time.
2. If it re-flags, open an upstream issue (pbakaus/impeccable) with the repro, and decide whether a
   local wrapper is worth it.
3. Remove the two dead `hook.mjs` entries from `settings.json`.

## Acceptance
- A recorded observation of the 4.5.0 Stop hook across consecutive turns, with the outcome.
- `settings.json` no longer references `scripts/hook.mjs`.
