<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=HARD, worth=6, reconfirm-count=1, content-hash=07d6e38d -->
<!-- duplicate-checked: follow-up to done 1136; the shutil.which fix now launches a pnpm shim that itself fails -->
# testing-floor node check fails through pnpm's managed-tools shim

**Type:** task
**Origin:** ai

## Goal

The Stop-hook testing floor's node check runs in a repo whose pnpm comes from pnpm's self-managed
tools dir.

## Context

Seen 2026-10-08 in cueline (session 3c23586b), right after todo 1136's fix landed (launcher resolved
via `shutil.which`). The WinError 2 is gone, but the check now fails with:

`node check failed (exit 1): ...'"C:\Users\tecno\AppData\Local\pnpm\.tools\pnpm\12.4.2\bin\\..\node_modules\pnpm\pnpm"' is not recognized as an internal or external command`

So the resolved `pnpm.cmd` is the managed-tools shim, and that shim fails when launched from the
hook's environment. In the same session Claude ran `npx tsc --noEmit` and `npx vitest run` from
Bash with no problem. UNVERIFIED why the shim breaks there (would check the shim's `%~dp0` handling
and whether the hook passes `shell=True` or a list argv to a `.cmd`).

Also seen: the rust half still timed out at 300s while a resumed builder was compiling; the 1136
deferral did not fire, possibly because a task-notification for that builder had already marked it
stopped while it was still running its own background work (UNVERIFIED).

## Acceptance

- In cueline, the hook's node check exits 0 when `npx tsc --noEmit` does.

## Notes

- 2026-10-08, loop-todos final review: cause found. `C:\Users\tecno\AppData\Local\pnpm\.tools\pnpm\12.4.2\bin\pnpm.CMD` is `@"%~dp0\..\node_modules\pnpm\pnpm" %*`, and that target is an extensionless script, so cmd.exe (and CreateProcess on a .cmd) can never run it; Git bash runs the extensionless `bin/pnpm` sh script instead, which is why Claude's Bash tool works. Mitigation shipped: a check whose output says "is not recognized as an internal or external command", or that times out, now counts as not verified instead of a failure, so the gate stops blocking on its own launch problems. Still open: actually running the node check through a launcher that works (e.g. Git bash `bash -lc "<pm> test"`, the environment Claude's own shell uses), which is what the Acceptance asks. The rust-timeout half is covered by the same not-verified change; why the 1136 deferral missed that builder is still UNVERIFIED.

## Answers 2026-10-08

- Joe, 2026-10-08 (todo-questions chat): approved to build as written (run the node check through Git bash).
