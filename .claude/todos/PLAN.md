# Plan

## Next up

- [ ] 351 - build `/ticket`: create/update/pickup only, platform looked up from the repo

**`/test` shipped 2026-08-18** (handoff 378 archived), the smallest complete instance of the
verb-first pattern: `skills/test/SKILL.md`, slash-only so it costs zero always-on description
budget, stack inferred from marker files across Flutter, Node/web, Rust/Tauri, Roblox/Luau and a
scripts-repo fallback, with e2e delegated to `/flutter-e2e` and `/jest-lua` rather than absorbed.
Joe settled all three open decisions in one card: **the automatic floor stays fast-checks-only**,
but Claude now says in one line when e2e looks worth running instead of asking (two new bullets in
`CLAUDE.md`); all four stacks in v1; slash-only invocation. **351 now carries the settled `/ticket`
scope** - create/update/pickup merged, `priorities` and `done-audit` left alone, and the tree-wide
router idea explicitly dead at 3/10.

**Still open from 375:** the `/linear` SKILL.md pointer to the ground check. Blocked three times now
because a concurrent session holds uncommitted changes in that file. Enforcement does not depend on
it - the guard's deny message already names the ref.

**The outbound gate shipped 2026-08-18** (Joe's pick for the first restructure build): Linear
creates and claim-bearing updates on both platforms are now gated by the shared ground check in
`refs/outbound-ground-check.md`. Todo 375 archived. Two bugs fell out of it, both fixed: a test
broken by my own rename, and a UTF-8 BOM in `~/.claude/.env` that had been making the Shortcut
owner check fail closed on every mutation.

**58 is DONE as of 2026-08-18**, along with its 366 pointer. Both archived. The audit triaged all 83
skills, ran 6 independent reviewers over 3 contested clusters, and **removed nothing** - the tree was
already clean after the 2026-08-01 pass. What it did fix was always-on context: **13 skills flagged
slash-only, cutting the per-session description budget from 10,445 to 5,892 chars (43.6%)**, plus 4
correctness fixes. Full record: `skills/AUDIT-2026-08-18.md`.

**Still open from 58:** the 15 high-usage core skills (`commit`, `close`, `code-check`,
`supervised-run` and the rest) got a mechanical pass only, never a dedicated improvement reviewer.

**18 active todos.** Updated 2026-08-17 after a NAMED-SUBSET `/auto-do-todos` run: Joe named five
ids (352, 354, 358, 359, 361) and all five landed. That run swept no backlog - no dedupe, no
premise re-verification, no dead-todo archival - because Steps 2-4 are skipped when the queue is
given, per the rule todo 358 itself added. The closing `/close` then filed three more (367, 368,
369), all from that run's own tooling friction.

The actionable queue was **thirteen** when 58 closed: 351, 353, 355, 356, 357, 360, 362, 363, 364,
365, 367, 368, 369. Concurrent sessions have since filed more (370, 371, 372, 373, 374, 376, 377,
379, plus two slug-only files with no id). **58 is done, so nothing gates ordering any more - run
`/plan-todos`**; only 351 is placed on the lane above.

**11, 30 and 362 were all ruled on by 58 on 2026-08-18, and none of them is parked any more:**

- **11** (`/orphan-audit`) - unblocked as a SCRIPT, not a skill. The doctrine already exists in
  `refs/process-hygiene.md`; what is missing is something runnable, and a script costs no description.
- **30** (`/story-shot`) - unblocked as a **fibo-local** skill. 418 Storybook shell calls in 31 days,
  but all inside one project family, so a global skill would bill every session for one repo.
- **362** (render-and-diff) - not a new global skill. Kept separate from `flutter-e2e` rather than
  bolted into it, and folded into the `/test` and `/e2e` direction Joe set out on 2026-08-18.

Per the contract in `~/.claude/skills/close/ai-todos-format.md`, claim each todo in
`.claude/todos/.claims/` before executing it, and archive with `complete-todo.ps1` when done.
**Ids are now reserved atomically** via `~/.claude/skills/close/reserve-todo-id.ps1`, never by
hand-scanning for max+1 - see the Resolved questions section.

## Parked (1)

**58 is done and archived** (2026-08-18). Scale after that pass: **32 model-invocable skills costing
5,892 always-on chars**, down from 45 / 10,445. Of the 12 vendored skills, the 11 Cloudflare-family
ones now carry a `disable-model-invocation` patch recorded in `skills/VENDORED.md` - **a re-vendor
silently drops it and grows the budget back by 4,243 chars with no error.**

**11 and 30 are NO LONGER PARKED.** 58 ruled on both (see Next up for the reasoning). They are
buildable work now, not blocked items:

- [ ] **11** - `/orphan-audit` as a SCRIPT under an existing skill, not a new skill
- [ ] **30** - `/story-shot` as a **fibo-local** skill in that repo's own `.claude/skills/`, not global

- **95** - session activity log. Not a checkbox on purpose. Joe's words on 2026-08-16: *"i think this
  deserves a whole session, its a question of permanent memory, something im very passionate for,
  but its best we shelf it for now, that should be brainstormed in its own session."* Its shape is
  now settled even though its content is not: **this is a `/brainstorm` task, not a build task
  waiting for a green light.** The old build-or-park question is closed.

## Actionable (10)

- [ ] **351** - unify the 8 ticket skills behind one platform-inferring `/ticket`. Joe's own idea,
  dev-origin. Sized as its own session, and overlaps 58, which would likely shrink it.
- [ ] **353** - three more inline `search/stories` recipes outside todo 343's named scope. Also
  carries the unresolved `+` versus `--data-urlencode` encoding question.
- [ ] **355** - `-GetId` can still answer confidently wrong from a background dispatch, and the
  script cannot detect it. Needs a background-dispatch measurement BEFORE any fix.
- [ ] **362** - render-and-diff a built screen against its design tile. **Park candidate** - new
  skill surface, see the header. Ask Joe before executing.

The rest are enforcement gaps of one kind or another - 356, 357, 360 and 363 are the shape the hook
doctrine below keeps rediscovering (a correct rule with nothing enforcing it), while 364 and 365 are
the inverse: a guard that IS enforced, contradicted or bypassed by the path that feeds it.

- [ ] **356** - running `/commit`'s prefilters and `git commit` in one shell call has no gate, so a
  flagged diff commits anyway. This actually happened, twice-em-dashed, in commit `8abd412`. The
  near miss is that `secret-scan` would have gone the same way. **Highest value of the ten.**
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
- [ ] **365** - two commit-guard session markers landed on malformed paths (unexpanded
  `$CLAUDE_CODE_SESSION_ID`, and a missing `/`), so one session wrote no usable marker at all.
- [ ] **367** - `complete-todo.ps1` never prunes a PLAN.md line written in the bold style, and
  reports the miss as if it succeeded. Five for five in one run; the stale lines only went away
  because PLAN.md was rewritten by hand afterwards. **Highest value of the new three.**
- [ ] **368** - `/commit`'s unpushed-overlap check fires on nearly every commit here, because this
  repo's unpushed window is 50-plus commits deep rather than one session's work.
- [ ] **369** - `/auto-do-todos` Step 6 mandates a subagent per todo even where CLAUDE.md says to
  edit inline. Third instance of this skill stating an absolute that real runs correctly ignore.

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
