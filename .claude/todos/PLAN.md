# Plan

71 active todos, grouped into 16 batches. Written 2026-08-11 after a full re-verification pass
over all 123 todos in the backlog at that time (13 agents, every premise re-checked against the
live tree). 45 were archived as dead, duplicate, or not worth building; the rest are below.

## How to use this file

**Claim a whole batch, not a single todo.** The batches exist because the backlog is not 68
independent items: it is a handful of subsystems each carrying a pile of papercuts. Nine separate
todos edit `skills/commit/SKILL.md`. Nine edit the clockify skill. Doing them one at a time means
re-reading the same file nine times, nine commits, and nine chances to conflict.

One batch is one session. Read every todo in the batch first, then plan the file's end state once,
then edit once.

**`/pickup` takes ONE todo per invocation, so it fights this grouping.** Use it for `58` (which is
a whole session on its own) or to resume a half-finished batch. To start a batch, say "do batch A
from PLAN.md" instead, and let the session claim each id in the batch as it goes.

Batches are independent of each other, so several sessions can run in parallel, as long as no two
take batches that name the same file.

Per the contract in `~/.claude/skills/close/ai-todos-format.md`, claim each todo in
`.claude/todos/.claims/` before executing it, and archive with `complete-todo.ps1` when done.

## Do this first

- [ ] **58** - audit `skills/` and decide keep / update / remove per skill (~78 skill dirs)

`**Origin:** dev`, Joe's own ask. It blocks **11**, **30** and **63**, which all propose new
skills or new skill capabilities that the audit might make redundant. It also answers the open
question about the 11 untracked vendored skill directories. Do not start batch D or the blocked
items until this lands.

## Batch A - `/commit` and build-watch (9)

All nine touch `skills/commit/`. Plan the file's end state once.

      clobbering, the worktree-unrunnable form, and the Rules-vs-step-5a contradiction at once)

## Batch B - clockify-reconciliator (9)

All nine touch `skills/clockify-reconciliator/`. Note **91** already shipped today.


## Batch C - delegation and autopilot (3)

`refs/delegation-doctrine.md` plus the autopilot skills. **53**, **78** and **92**'s siblings
already shipped today.


## Batch D - screenshot and Playwright (3, blocked on 58)

- [ ] 63 - one multi-frame helper (absorbed 44, 72, 236: frame matrix, comp rendering, playwright resolution)
- [ ] 30 - storybook restart-wait-screenshot loop

## Batch E - close and session identity (4)


## Batch F - Shortcut family (6)


## Batch G - create-pr (3)


## Batch H - rate-it family (3)

      where `send_message` is the only channel Joe sees

## Batch I - supervised-run (3)


## Batch J - brainstorm (2)


## Batch K - impeccable (3)


**62 and 71 are at risk.** The fixes are live on disk but `skills/impeccable/` is untracked, so
reinstalling or updating the skill silently reverts both. Resolve the tracking question first.

## Batch L - single-file wins (8)

No shared file, no design forks. Good batch for a short session.

- [ ] 11 - orphan-process forensics gets rewritten ad hoc every time (blocked on 58)

## Batch M - odds and ends (4)

Unrelated to each other; pick off individually.

      `_hooklib.py`. The BOM fail-open bug had to be fixed five times because of this
      2026-08-11 and not triaged by the 2026-08-11 pass.** Note its id collides with the archived
      `done/249-commit-comment-noise-pipeline-vs-no-chaining-rule.md`

## Not in this repo (3)

Each changes something outside `~/.claude`. Move them or do them where they belong.

Deliberately NOT checkboxes, so `/pickup` never serves them as the next lane item.

- 32 - compact **fibo's** `MEMORY.md` (156 lines, target under 140)
- 247 - repair pass over external public repos. Rediscovered 2026-08-13: it is **15 repos, not 8**,
      and the pass also caught `mass_send_message` being dead in production (its Vite `base` is
      `/MassSendMessage/` while Pages serves `/mass_send_message/`, so the main bundle 404s).
      Authorized by Joe, push direct, in flight.
- 88 - done, archived 2026-08-13 on Joe's call as not worth tracking.

## Parked - do not build (2)

Not checkboxes on purpose. `/pickup` must never hand these to anyone as actionable.

- 95 - session activity log. Joe explicitly stopped the build 2026-07-30. The file exists to
      preserve the research so it is not rediscovered. Leave it alone.
- 240 - autopilot text marker to MCP tool. Blocked on `claude_usage_in_taskbar` todos 435 and
      426, both confirmed still open.

## Deferred by decision (1)

- 02 - auto-commit stop hook. Joe adopted "hooks guard destructive actions, prose guards
      style" on 2026-08-11, which built 18, 65, 76 and 98. This one stayed unbuilt: a prior
      `/iterate-it` run converged at 5/10, and its scoping premise went stale when auto-commit
      widened from full-auto repos to every repo. Revisit only with a better design.

## Open questions for Joe

All three were answered on 2026-08-13. Kept here with their resolutions so nobody re-asks.

1. **Vendored skills: RESOLVED, but not the way the question assumed.** The wholesale commit had
   already happened in `4cc2977` (2026-08-12, 516 files), which is the option `/rate-it` scored
   4/10. Real state now: 76 skill dirs, 669 files, 664 tracked. Joe chose the manifest, so
   `skills/VENDORED.md` was written as documentation over the existing state rather than as a
   tracking change. It found exactly ONE local patch in the whole vendored set,
   `skills/impeccable/reference/new-work.md`, verified by diffing against the vendoring commit.
   Still open, narrowly: whether to `git rm --cached` the ~516 unpatched vendor files to restore
   the exclude-vendored model. Nobody has to, and the silent-revert risk is one file wide.
2. **`hooks/` gitignored: RESOLVED.** Now tracked (`bcaa730`), 13 files, secret-scanned first.
   Joe asked whether the absolute paths could go too. Answer, VERIFIED against the live hook docs:
   `${CLAUDE_PROJECT_DIR}` is real and documented, but it resolves to whichever project is open,
   and this `settings.json` is the GLOBAL user-level file whose hooks fire in every session. A
   portable form would therefore break everywhere except this repo. Absolute paths stay, on
   purpose.
3. **corepack guard: RESOLVED, keep it strict.** Joe confirmed after learning it is a different
   thing from the package-safety rule: this one governs WHICH binary installs, never what gets
   installed. A global Yarn 1 once silently rewrote a Yarn 4 lockfile, which is the incident it
   prevents.
