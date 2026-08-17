# Plan

**13 active todos.** Updated 2026-08-17 after a NAMED-SUBSET `/auto-do-todos` run: Joe named five
ids (352, 354, 358, 359, 361) and all five landed. That run swept no backlog - no dedupe, no
premise re-verification, no dead-todo archival - because Steps 2-4 are skipped when the queue is
given, per the rule todo 358 itself added.

Four are parked by Joe, so the actionable queue is **nine**: 351, 353, 355, 356, 357, 360, 362,
363, 364. Run `/plan-todos` to order them.

**362 is a park candidate nobody has ruled on.** It proposes a new render-and-diff skill, which is
new skill surface - the exact reason 11 and 30 sit parked behind 58. It is listed as actionable
only because Joe has not been asked; ask before executing it, do not just run it.

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

## Actionable (9)

- [ ] **351** - unify the 8 ticket skills behind one platform-inferring `/ticket`. Joe's own idea,
  dev-origin. Sized as its own session, and overlaps 58, which would likely shrink it.
- [ ] **353** - three more inline `search/stories` recipes outside todo 343's named scope. Also
  carries the unresolved `+` versus `--data-urlencode` encoding question.
- [ ] **355** - `-GetId` can still answer confidently wrong from a background dispatch, and the
  script cannot detect it. Needs a background-dispatch measurement BEFORE any fix.
- [ ] **362** - render-and-diff a built screen against its design tile. **Park candidate** - new
  skill surface, see the header. Ask Joe before executing.

Five are the same shape the hook doctrine below keeps rediscovering: a correct rule with nothing
enforcing it.

- [ ] **356** - running `/commit`'s prefilters and `git commit` in one shell call has no gate, so a
  flagged diff commits anyway. This actually happened, twice-em-dashed, in commit `8abd412`. The
  near miss is that `secret-scan` would have gone the same way. **Highest value of the nine.**
- [ ] **357** - the orphan-check preamble line is gated on "runs Node commands", so a subagent's
  whole-drive `find` escaped it and then falsely reported itself killed. Third instance of a builder
  misreporting a process it started.
- [ ] **360** - a builder's verification method could not in principle prove the feature worked
  (synthetic DOM events passing while the real drag was broken), and the report was accepted anyway.
- [ ] **363** - the content-duplicate guard in `close/ai-todos-format.md` is documented and
  unenforced.
- [ ] **364** - following `/mega-todos` verbatim gets the dispatch rejected by
  `dispatch-preamble-guard.py`, because the skill removes a string the hook hard-requires. Touches
  the same injected block todo 361 just fixed, but a different failure in it.

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
