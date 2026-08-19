# Plan

## Next up

**14 todos. Nothing is ordered yet: run `/plan-todos`.**

A `/mega-todos` run on 2026-08-19 closed **33 todos in one pass**, 16 file-ownership lanes, one
commit per todo. Zero silent drops (reconciled as a set difference, not a count), zero barrier
failures, zero blocked builders. The full record is in each todo's own Notes line under `done/`.

Its own wrap-up then filed **twelve** new ones, which is the honest shape of a run that wide: three
lanes shipped something correct that was not wired up, because the wiring lived in a file another
lane owned.

- **392** - sweep the remaining skills whose dispatch templates miss the guard's three markers
- **393** - `claim-todo.ps1`/`complete-todo.ps1` reject a slug-only id the contract calls valid
- **394** - settle how Conductor's card parser reads markers (needs a live session)
- **395** - move the advanced-but-not-finished outcome into the contract, not just `/pickup`
- **396** - the clockify config template omits the two new HubStaff label fields
- **397** - `outbound-ground-check.md` names two of the four hooks that enforce it
- **398** - verify whether Shortcut decodes a literal `+` as a space
- **399** - the comment cap is unenforced for Python docstrings and PowerShell help blocks
- **400** - two model-invocable skill descriptions are over the always-on budget
- **401** - `design_diff.py` duplicates figma-pixel-diff's pixel sampler
- **402** - `oldest_fresh_marker` reads as a dead import in three guards
- **391** - builders have no sanctioned way to take a whole-tree baseline (filed by a builder itself,
  which violated the contract's no-subagent-writes rule; the finding is real, the channel was wrong)

Four gaps the run left were fixed immediately rather than filed: the duplicate-guard hook was never
wired into `settings.json` (`5f9bf9e`), `/commit` still hand-built the session-marker path instead of
calling the new helper (`f615d51`), the doctrine still gated the orphan check on Node (`45cff85`),
and the newly-wired duplicate guard false-positived on every write until it learned document
frequency (`29debda`).

## Parked (2) and skipped (1)

- **95** - session activity log. Not a checkbox on purpose. Joe's words on 2026-08-16: *"i think this
  deserves a whole session, its a question of permanent memory, something im very passionate for,
  but its best we shelf it for now, that should be brainstormed in its own session."* Its shape is
  now settled even though its content is not: **this is a `/brainstorm` task, not a build task
  waiting for a green light.** The old build-or-park question is closed. Scored 2/10 on worth by
  `/cleanup-todos` 2026-08-19 and deliberately NOT archived: a parked-by-the-dev todo is the
  rubric's own carve-out, the score is measuring the wrong thing.
- **391** - a builder needing a whole-tree "before" baseline has no sanctioned mechanism, so it
  reaches for `git stash` in a tree other agents are working in. Filed 2026-08-19. Note that the
  builder filed this **itself**, violating the contract's "a subagent never writes into
  `.claude/todos/`" rule (see `refs/delegation-doctrine.md`, Out-of-scope findings). The finding is
  real and kept; the channel was wrong.
- **372** - move the 419-file / 55.7MB Playwright profile out of `skills/`. `**Origin:** dev`, so it
  never auto-executes. Joe explicitly skipped it on 2026-08-19: the `.gitignore` stopgap already
  neutralises the harm, and a botched profile move costs a HubStaff re-login. Cleanliness, not
  correctness.

## What the 2026-08-19 run settled

**Todo 30 left this backlog.** `/story-shot` is now fibo's todo `258`. The 58 audit ruled it a
fibo-local skill (418 Storybook calls in 31 days, all one repo family), which reversed the
2026-08-07 decision to move it here. Joe confirmed the reversal. The location history is written
into the fibo file so it does not get re-litigated a fourth time.

**`/test` split into `/test` and `/e2e`** on Joe's call, reversing what he concluded on 2026-08-18.
`/test` is fast checks only; the new `skills/e2e/SKILL.md` owns browser-driven runs and delegates to
`/flutter-e2e` and `/jest-lua`. `CLAUDE.md`'s testing bullet no longer says `/test` means unit AND
e2e. Todo 362's render-and-diff landed as a **mode on `/e2e`**, not a third global skill, so it cost
no new always-on description budget.

**Todo 389's premise was disproven, not implemented.** The builder reproduced the failure in a
scratch repo and found the cause is PowerShell mistokenizing a native `git -m` argument containing a
literal double quote, identically inline and via a variable. The todo's own "assign to a variable
first" theory was wrong. The fix is backslash-escaping, and that is what got documented.

**Two bugs were reproduced live by the run itself**, which is the strongest evidence either could
have had:

- **367** - `complete-todo.ps1` failed to prune `- [ ] **30**` when archiving todo 30, and reported
  success. Fixed, then the fix immediately exposed a second defect: the widened regex pruned only
  the FIRST line of a wrapped list item, orphaning its continuation prose and mangling ten entries
  in this file. Both are fixed now; the multi-line prune is covered by a scratch-repo test.
- **365** - both malformed session-marker strays were physically in the tree that morning.

**Known script/contract mismatch, still open.** `claim-todo.ps1` and `complete-todo.ps1` both reject
a slug-only todo id, even though `close/ai-todos-format.md` says the full filename stem is a valid
`-Id`. The three slug-only todos in this run had to be claimed and archived by hand. Worth a todo
next time someone touches those scripts.

## Resolved questions, kept so nobody re-asks

1. **Todo id allocation is now atomic.** `reserve-todo-id.ps1` writes an `<id>-.reserved` marker with
   no-overwrite semantics before the real file, the same primitive `claim-todo.ps1` proves for the
   claims mutex. Proven with two real concurrent processes doing 25 reservations each: 50 ids, zero
   duplicates. Abandoned reservations self-heal on the 4h-plus-dead-pid rule. Markers are gitignored.
   Joe rejected non-sequential ids (readable ordering matters) and rejected hardening the reactive
   rename-on-collision guard, which had already been tried in `c971a08` and failed anyway.
2. **Session markers moved** to `hooks/.session-markers/<session_id>`, out of reach of a
   non-recursive `hooks/.commit-marker-*` glob. A permanent read-only legacy fallback covers
   stragglers. This is the structural half of todo 341; the preamble also now bans glob cleanup.
   As of todo 365 the write itself goes through `hooks/write-session-marker.ps1`, which either lands
   the marker at the right path or errors rather than silently concatenating.
3. **Vendored skills.** The wholesale commit already happened in `4cc2977` (2026-08-12, 516 files).
   `skills/VENDORED.md` found exactly ONE local patch in the whole vendored set,
   `skills/impeccable/reference/new-work.md`. Narrowly still open: whether to `git rm --cached` the
   ~516 unpatched vendor files. Nobody has to; the silent-revert risk is one file wide.
4. **`hooks/` is tracked** as of `bcaa730`, secret-scanned first. The absolute paths in
   `settings.json` stay on purpose: `${CLAUDE_PROJECT_DIR}` resolves to whichever project is open,
   and that file is the GLOBAL user-level settings whose hooks fire in every session.
5. **The corepack guard stays strict.** It governs WHICH binary installs, and a global Yarn 1 once
   silently rewrote a Yarn 4 lockfile.
6. **`/brainstorm` deliberates first** as of 2026-08-16. It shows a plan capped at ~5 lines and
   waits, unless the invocation carries a go-word ("then implement it", "just do it", "go") or the
   change is a single existing file adding no new file and no new skill/hook/rule surface. The
   gate-free promise now covers only those two escapes.
7. **`/commit` now has teeth it used to lack**, all landed 2026-08-19: `prefilter-gate.sh` makes a
   flagged diff structurally unable to commit (356), step 8 requires a `git diff` of every pathspec
   entry before committing (377) and a `rev-parse` readback of the real sha after (379), step 6a
   detects a real test suite when no `run-tests` skill exists (383), and the unpushed-overlap check
   confirms via `git blame` instead of firing on every commit in a 50-deep unpushed window (368).

## Hook doctrine, and what the 2026-08-16 run added to it

The 2026-08-13 lesson stands and got two more data points:

- **Exact mechanical checks ship.** `hooks/em-dash-guard.py` is live because U+2014 is a codepoint.
  Two more shipped on 2026-08-16 on the same basis: `dispatch-preamble-guard.py` (three verbatim
  string checks, with a `READ-ONLY DISPATCH` opt-out marker rather than a guess about read-only-ness)
  and `ui-screenshot-reminder.py` (path-extension gate, fails open, once per session).
- **Heuristic judgment calls do not.** The unverified-mechanism detector hit 67 percent false
  positives, the bare-question detector missed 20 to 25 percent against ~4025 real messages, and the
  command-chaining detector flagged 55 percent of 30047 real commands. All three stay as
  `hooks/EXPERIMENTAL-*.py` with their measurements.
- **Measuring can also SAVE a change.** Todo 342 measured three match scopes against 7128 real
  prompts. `whole_prompt` would have caught every invocation but also fired inside all 131
  task-notification bodies, reproducing the exact injection bug todo 332 fixed. The middle option
  won on evidence: +74 genuine catches, zero new false positives. Writeup in
  `hooks/flagged-skill-mention.md`.

Measure against a real corpus BEFORE wiring anything, and prefer inverting the problem (require an
explicit marker on the legitimate case) over detecting the violation.

The 2026-08-19 run added a fourth guard on the same principle: `hooks/todo-duplicate-guard.py` (363)
is advisory with an override path rather than a hard block, precisely because "is this todo a
duplicate" is a judgment call and this repo has already killed three guess-based hooks in one day.
