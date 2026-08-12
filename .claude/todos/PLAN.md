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
- [ ] 36 - working-tree safety when a pre-commit hook runs on a shared `.git` (real data-loss incident)
- [ ] 105 - make step 1's commit-style.md read an enforced precondition

## Batch B - clockify-reconciliator (9)

All nine touch `skills/clockify-reconciliator/`. Note **91** already shipped today.

- [ ] 34 - full-month audit / reconstruction mode (methodology already proven live twice)
- [ ] 82 - consult existing memory, and handle "day has entries but real work unlogged"
- [ ] 90 - opt-in HubStaff align step, plus the per-entry coverage fix in step 11

## Batch C - delegation and autopilot (3)

`refs/delegation-doctrine.md` plus the autopilot skills. **53**, **78** and **92**'s siblings
already shipped today.

- [ ] 01 - detect dead or stalled background subagents
- [ ] 50 - guard session budget, not just context, on wide fan-outs

## Batch D - screenshot and Playwright (3, blocked on 58)

- [ ] 63 - one multi-frame helper (absorbed 44, 72, 236: frame matrix, comp rendering, playwright resolution)
- [ ] 30 - storybook restart-wait-screenshot loop
- [ ] 74 - the "release build, not DWDS" guidance is stale; needs cross-app retesting first

## Batch E - close and session identity (4)

- [ ] 60 - use `CLAUDE_CODE_SESSION_ID` instead of the unreliable ancestor-pid walk (absorbed 54)

## Batch F - Shortcut family (6)

- [ ] 97 - no skill covers updating existing stories; a bare PUT wipes `custom_fields`
- [ ] 234 - port the bash pagination to python, widen the git cross-check, add a liveness probe
- [ ] 86 - ground "implement X flow" tickets in current code before drafting

## Batch G - create-pr (3)


## Batch H - rate-it family (3)

      where `send_message` is the only channel Joe sees

## Batch I - supervised-run (3)

- [ ] 238 - verify `/run` actually routes through the supervisor (mostly a verification task)

## Batch J - brainstorm (2)

- [ ] 242 - decide whether to widen the step-2 ask gate, or record why it stays narrow

## Batch K - impeccable (3)


**62 and 71 are at risk.** The fixes are live on disk but `skills/impeccable/` is untracked, so
reinstalling or updating the skill silently reverts both. Resolve the tracking question first.

## Batch L - single-file wins (8)

No shared file, no design forks. Good batch for a short session.

- [ ] 246 - `bepy-project-setup-web`: drop the skip-picker, run everything by default
- [ ] 49 - `/auto-do-todos` has no path for an explicit cleanout request
- [ ] 11 - orphan-process forensics gets rewritten ad hoc every time (blocked on 58)

## Batch M - odds and ends (4)

Unrelated to each other; pick off individually.

- [ ] 229 - `/obsidian` rewrite: free-form args, People branch, fix the `Journal/` grep
- [ ] 231 - sentry: absolute ACT-bucket severity floor and pagination past `limit=100`
- [ ] 250 - the five guard hooks each re-implement the same scaffold; decide on a shared
      `_hooklib.py`. The BOM fail-open bug had to be fixed five times because of this
      2026-08-11 and not triaged by the 2026-08-11 pass.** Note its id collides with the archived
      `done/249-commit-comment-noise-pipeline-vs-no-chaining-rule.md`

## Not in this repo (3)

Each changes something outside `~/.claude`. Move them or do them where they belong.

Deliberately NOT checkboxes, so `/pickup` never serves them as the next lane item.

- 32 - compact **fibo's** `MEMORY.md` (156 lines, target under 140)
- 247 - repair pass over 8 external public repos; the og:image defect is confirmed still live
- 88 - revoke a stale HubStaff PAT (Joe's browser, zero functional impact)

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

1. **`skills/` has 11 untracked vendored directories** (~517 files: impeccable, the Cloudflare
   set, agents-sdk, wrangler and more). A `/rate-it` on committing them wholesale scored **4/10**;
   the recommendation was a manifest of installed skills plus versions, and committing only the
   files that have been locally patched. Blocks batch K.
2. **`hooks/` is gitignored while `settings.json` is tracked.** Settings references the hook
   scripts by absolute path, so a fresh clone gets wiring that points at files which do not exist.
   Unlike the vendored skills these are hand-written and irreplaceable.
3. **The package-manager guard requires `corepack yarn install`** over bare `yarn install` in any
   pinned repo, even when the PATH binary already matches. One line to relax if it grates.
