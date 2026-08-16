# Plan

**12 active todos.** Updated 2026-08-16 after an `/auto-do-todos` run took the backlog from 18 down
to 9: **17 executed, 1 archived as superseded, 5 filed** (1 from Joe, 4 from the run's own findings).
The closing `/close` retrospective then filed 3 more, taking it to 12. Every `## Open questions`
block that was waiting on Joe is now answered and gone.

Four of the twelve are parked by Joe's own decision, so the real actionable queue is **eight**: 351
through 358. Run `/plan-todos` to order them; that queue is now past the point where doing it by
hand is worth the effort.

Per the contract in `~/.claude/skills/close/ai-todos-format.md`, claim each todo in
`.claude/todos/.claims/` before executing it, and archive with `complete-todo.ps1` when done.
**Ids are now reserved atomically** via `~/.claude/skills/close/reserve-todo-id.ps1`, never by
hand-scanning for max+1 - see the Resolved questions section.

## Parked by Joe, reconfirmed 2026-08-16 (4)

Joe was asked about all four in this run's question round and kept every one parked. Do not re-ask,
and do not open them as side quests.

- [ ] **58** - audit `skills/` and decide keep / update / remove per skill

His third deferral. Current scale is **76 directories, 669 files, 664 tracked**, of which **12 are
vendored** (11 Cloudflare-family skills plus `impeccable`), documented in `skills/VENDORED.md`.
Judge those 12 on "do we still want this installed" rather than on quality.

- [ ] **11** - `/orphan-audit`, process forensics gets rewritten ad hoc every time
- [ ] **30** - `/story-shot`, the Storybook restart-wait-screenshot loop

Both blocked on 58. They add NEW skill surface, which is exactly what the audit might prune. Joe was
offered the option to lift the block and declined.

- **95** - session activity log. Not a checkbox on purpose. Joe's words on 2026-08-16: *"i think this
  deserves a whole session, its a question of permanent memory, something im very passionate for,
  but its best we shelf it for now, that should be brainstormed in its own session."* Its shape is
  now settled even though its content is not: **this is a `/brainstorm` task, not a build task
  waiting for a green light.** The old build-or-park question is closed.

## Actionable (5)

- [ ] **351** - unify the 8 ticket skills behind one platform-inferring `/ticket`. Joe's own idea,
  dev-origin. Sized as its own session, and overlaps 58, which would likely shrink it.
- [ ] **352** - `/autopilot` and `/delegate` still carry the commit-cadence ambiguity todo 347 fixed
  in the other three files. Consistency work, small.
- [ ] **353** - three more inline `search/stories` recipes outside todo 343's named scope. Also
  carries the unresolved `+` versus `--data-urlencode` encoding question.
- [ ] **354** - `hooks/.claude/last-session-status.json` is untracked and unignored, so it shows in
  every `git status`. Small.
- [ ] **355** - `-GetId` can still answer confidently wrong from a background dispatch, and the
  script cannot detect it. Needs a background-dispatch measurement BEFORE any fix.

The last three came out of that run's own `/close` retrospective, and all three are the same shape
the hook doctrine below keeps rediscovering: a correct rule with nothing enforcing it.

- [ ] **356** - running `/commit`'s prefilters and `git commit` in one shell call has no gate, so a
  flagged diff commits anyway. This actually happened, twice-em-dashed, in commit `8abd412`. The
  near miss is that `secret-scan` would have gone the same way. **Highest value of the eight.**
- [ ] **357** - the orphan-check preamble line is gated on "runs Node commands", so a subagent's
  whole-drive `find` escaped it and then falsely reported itself killed. Third instance of a builder
  misreporting a process it started.
- [ ] **358** - `/auto-do-todos` Steps 2-3 are marked "always runs", but a real run substituted a
  triage subagent. Same contract-versus-practice gap as 347.

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
