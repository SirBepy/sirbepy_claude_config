# Plan

## Harvest implementation - ordered, 2026-08-20

**33 todos from the open-source `.claude` harvest: 414-444, plus 450-451 from Joe's own review of the
report.** Full findings in `refs/harvest-2026-08-20-oss-claude-repos.md`. Ordered by RISK ASCENDING,
not by value: 8 of them edit `hooks/` or `settings.json`, where a mistake is silent and breaks every
future session, and Joe does not read code. So the safety net comes first and the blast radius comes
last.

**One fresh chat per phase.** The todos were deliberately written so a cold session executes from the
file alone; carrying harvest context forward buys nothing and costs the context the work needs.
`/mega-todos` is the proven machinery for a phase (33 todos closed in one pass on 2026-08-19, one
commit per todo, zero drops) but note many of these touch the SAME files, so file-ownership lanes
matter and the marked sequences must stay sequential.

### Phase 0 - safety net. DONE 2026-08-20.

Push landed, and 423 shipped `ci/run_all.py` plus `.github/workflows/ci.yml`. Every later phase now
has a mechanical check: `python ci/run_all.py` runs every `hooks/test_*.py` self-test suite,
validates skill frontmatter across all 83 skills, and gates `CLAUDE.md` at 6732 tokens. `/commit`
step 6a runs it too, so a local pass and a green CI run mean the same thing.

**The token ceiling has ZERO headroom by design** (6732 is the measured current weight), so phase 4
(429, 442) cannot add a `CLAUDE.md` rule without either cutting elsewhere or raising `CEILING_TOKENS`
deliberately. That is the ratchet working, not a bug to route around.

### Phase 1 - the three real defects. DONE 2026-08-20.

414, 415 and 416 all landed, one commit each. 414 fixed the lying docstring and its sweep found no
second one. 416 DELETED the three unadopted spikes, so `hooks/` is now all-live and CI discovers 11
suites, not 13. 415 moved the impeccable and status-marker-guard wiring into the tracked
`settings.json`, both proven live by real nested-session triggers; `settings.local.json` stays
untracked and now says so in its own `description`.

### Phase 2 - security. DONE 2026-08-21.

418, 420 and 419 all landed, one commit each. 418 shipped `/supply-chain-audit`, a read-only
`context: fork` skill proven on three live runs. 420 shipped the write-time secret scan and the
sensitive-file guard, both `ask` not `deny`, sharing one pattern source with `/commit`'s prefilter.
419 shipped the tiered destructive-command guard, `CLAUDE_HOOK_PROFILE` defaulting to `standard`.

**The phase's real lesson, worth more than the three guards:** a corpus proves only that no PAST
command tripped a rule. All eleven CORE rules measured 0 hits across 62,270 real commands, and the
guard still had **three separate false-positive classes** that only hand-probing found, two of them
caught by the guard denying its own author's commands minutes after going live. Measure first, then
probe the built thing by hand. Neither step substitutes for the other.

**Heads-up for phase 6 and 7, which do harness surgery:** 420's `sensitive-file-guard.py` now asks on
every write under a `.claude/hooks/` directory and on every `settings*.json` write. Measured at 288
prompts across 22,992 historical writes, so a hook-heavy phase will see several per session. That is
deliberate (an agent that can edit its own guards has no guards), not a bug to route around.

### Phase 3 - skill quality. DONE 2026-08-22.

422, 421 and 436 all landed, one commit each. 422 shipped `tools/skill_eval.py`: each fixture runs
in a fresh `claude -p` process and is graded by a SECOND process launched with every file, exec and
delegate tool denied and no mention of which skill produced the text, so the grader's independence
is a property of the dispatch. `tools/test_skill_eval.py` rebuilds every real grader prompt in CI
and fails if one echoes any 12-word run of the skill under test. 421 added `/rate-it`'s adversarial
verification pass (its lens isolation was already shipped in `fa3dcf8`, so that half of the todo was
stale). 436 shipped `/heal-skill`, manual-only, with a taxonomy rewritten from this repo's own
failures after the upstream one was tested and failed.

**The phase's real lesson, and it is the same shape as phase 2's:** the harness did not catch its
first TWO deliberate regressions, and the fixtures were the defect. Fixture 5 graded conditional
behaviour unconditionally, so a correct answer using `/rate-it`'s own no-lift escape hatch failed
four assertions, and the fixture's own variance ran 6/6 to 1/6 against an unmodified skill. A
measurement whose noise is five expectations wide cannot detect a deleted section. Once the
assertions were made conditional the same mutation was caught cleanly, 18/18 against 11/18.
**A single-run pass rate from this harness is noise.** Use `--repeat 3` or higher, and read the
per-expectation stability table rather than the headline percentage.

**Two costs to know before using it.** A 6-fixture pass with fresh executors is about $2.90. A
panel fixture is about $2 on its own because it spawns 6 subagents, and running two of them hit the
**account session limit** mid-run, which kills the nested processes outright. Budget panel work, and
expect to retry after a reset.

**Also useful for phase 4 onward:** the same before/after machinery works on any skill, and
`/heal-skill` will hand a patch to it. Two findings that fell out of phase 3 are filed rather than
fixed: 475 (`/rate-it` states two different bullet caps 7 lines apart) and 477 (`skills/wrangler/
SKILL.md` at 923 lines is the one real progressive-disclosure outlier out of 85 skills; the sidecar
convention is otherwise already the norm). 476 records a third false-positive class on the
shell-write guard, hit while doing this work.

### Phase 4 - CLAUDE.md weight and rules. DONE 2026-08-22.

424, 429 and 442 all landed, four commits (`2b49016`, `1a830f2`, `2e2296c`, `74e3aff`).
**`CLAUDE.md` went 6732 -> 6558 tokens and `CEILING_TOKENS` was ratcheted down to match**, back to
zero headroom. That is a 412-token cut minus 206 spent back on three new rules.

**424 did NOT ship a `.claude/rules/` tree, and the reason is worth carrying forward.** The
mechanism is real and was verified two ways (the loader inside the `claude` binary, plus four live
nested `claude -p` runs): the frontmatter field is `paths:`, a junction into the config dir loads,
and glob matching is gitignore semantics. **But its only trigger is the `Read` tool.** Write and
Edit never load a scoped rule, so every rule the todo named (icons, persistence, the comment
budget) would have stopped firing on file creation, which is when they matter most. The full
verified behaviour is written into `done/424-*.md` so nobody re-derives it. The creation-path gap
is now todo **493**.

What shipped instead: 11 incident narratives moved into `refs/incidents.md`, leaving every rule
sentence in place. That property is mechanically checkable, and was checked - every removed
fragment begins with "Past incident" or "Decided 2026-08-18".

429 shipped the Timeless Present rule plus `skills/commit/comment-tense.sh` in the prefilter gate,
and deliberately did NOT ship the strength-tagging half; the audit ran instead and is in
`refs/claude-md-rule-force-audit.md`, with a re-open trigger. 442 shipped the evidence rule for
own-codebase claims and the deferred-work rule, and skipped the line-count ratchet.

**The phase's lesson, and it is a new shape:** verification tells you how a mechanism behaves, and
says nothing about whether to use it. `.claude/rules/` passed every behavioural test put to it and
was still the wrong tool, because `code-style/`'s content was never in the gated budget in the
first place - converting it would have bought **44 tokens** in exchange for a mechanism no check in
`ci/run_all.py` can test. That was arithmetic, not a probe, and no amount of further verification
would have surfaced it.

**A second lesson, less flattering.** A 4-lens `/rate-it` panel with an adversarial verifier pass
overturned the recommendation 4/4 and caught **two wrong numbers** in the briefs it was given: the
800-line commit fire rate (claimed 2 of 119, actually 5 of 118) and the `CLAUDE.md` bullet count
(claimed ~150, actually 81). The first was inferred from a percentile instead of counted, which is
the third recurrence of that class here (see `done/270`). The panel earned its cost on the
arithmetic alone. Note also that the verifier pass then **refuted the majority preference on 442** -
three of four raters preferred a option whose central premise (that extending `comment-noise.sh` is
near-free) does not survive reading the script. Raters converging is not evidence.

### Phase 5 - the review loop Joe actually asked for, plus discipline skills. DONE 2026-08-22.

451, 450 and 425 all landed, three commits (`6643b7c`, `37b5b8c`, and this one). 451 shipped
`/code-check`'s Step 4a class taxonomy plus the drop log; 450 shipped the fresh-reviewer property
and deferred its trigger; 425 adopted two methods as `refs/` files and skipped three skills.

**The phase's lesson, and it is a measurement lesson three times over.** Every one of the three
todos had its central premise or recommendation overturned by counting something:

- **451's premise was false.** It assumed refactor findings are write-only waste because Joe never
  reads code. He does not, and it does not matter: 18 `/code-check` findings, **13 executed, 1
  dropped, 4 open**, and **zero of the 13 executed by Joe naming an id** - batch runners drained
  every one. "He does not read the code" and "the finding never happens" are different claims.
- **450's isolation was never held anywhere.** The todo assumed a fresh reviewer was a property of
  firing EARLIER. In fact `skills/close/SKILL.md:149` invoked `/code-check` via the Skill tool, in
  the authoring session, and `CLAUDE.md:27` says subagents cannot invoke skills at all. The thing
  the todo wanted was missing from the path it already had.
- **425's five candidates all lost on the same fact**, which none of them were judged on
  originally: a skill cannot reach a subagent, and subagents do the work. Two became `refs/` files
  reached from the builder preamble; three were skipped.

**Every phase-5 recommendation I made was wrong before a panel corrected it, and the corrections
were arithmetic, not taste.** The 425 design scored 4/10, the 450 design 3/10. Three numbers I
published were wrong and caught by raters: a per-dispatch token cost measured off the wrong class
of subagent, a count of six dangling skill references reported as two, and a `mutation-testing`
skip argued from this repo's own file composition when `~/.claude` is GLOBAL config whose skills
fire in client repos. That last one is the newest trap and worth naming: **for anything in this
repo, the denominator is usually not this repo.**

The one thing that went right by accident is the most reusable. A mechanical dead-symbol scan
flagged `hooks/_hooklib.py`'s `strip_quotes` as unreferenced; two guards import it under an alias,
deleting it would have failed both closed across every session, and `ci/run_all.py` would still
have printed 4/4 green because **six live guards have no test file** (todo **501**). That is why
`/code-check` Step 4a now requires naming the command that would fail before applying anything.

**450 was SPLIT on 2026-08-22 by Joe.** Its fresh-reviewer half shipped; its trigger half moved to
phase 6 behind 427. The reason is worth carrying: the todo assumed isolation was a property of
firing earlier, and the review was in fact running **inside the authoring session all along** -
`skills/close/SKILL.md:149` invoked `/code-check` via the Skill tool, and `CLAUDE.md:27` says
subagents cannot invoke skills. `/code-check` now dispatches its own analysis. The `Stop`-hook
trigger rated a median 3/10 across a 3-lens panel plus verifier: a `decision: block` only
re-injects text into the session that wrote the code, so it cannot make anything structural, and
`/close` Phase 2 already carries a tuned 50-added-line floor the design was about to discard.

### Phase 6 - harness surgery. Highest blast radius, so last.

- [ ] 427 - Stop-hook verify gate. **Runs on every turn end. Build the escape hatch first.**
- [ ] 450 - the post-write TRIGGER half only. **Gated on 427's source-file-edited signal**; build
      it once, not twice. Full flaw list and the rejected `claude -p` alternative are in the todo.
- [ ] 426 - PreCompact, PermissionRequest, generic PostToolUse; the unused JSON control fields
- [ ] 434 - per-agent hooks, which could make the delegation ban list real instead of prose
- [ ] 437 - OS sandbox namespace. Likely only `credentials.mask` survives contact.

### Phase 7 - evaluations. "No" is an acceptable outcome for several of these.

- [ ] 431 - declarative hook engine. **Expected to close negative**; the 27 guards encode incident history a config row cannot hold.
- [ ] 433 - config layering. Likely a five-line move, not an architecture.
- [ ] 444 - prove-it-works / analytical Q&A / MCP scoping. Joe already judged prove-it-works redundant with `/test` and `/e2e`.
- [ ] 430 - cross-model delegation. Close it without building if the disagreement protocol has no answer.
- [ ] 438 [P] - permissions deny list (noise half is the real win; namespacing is probably a no)
- [ ] 440 [P] - config-protection guard. Gated on 427's signal.
- [ ] 441 [P] - `/supervised-run` enforcement
- [ ] 439 [P] - config-default deep-merge. Gated on 415.
- [ ] 443 [P] - `/create-pr` body anti-patterns
- [ ] 428 [P] - repo README, CONTRIBUTING, generated skills index
- [ ] 432 [P] - local statusline, kill the per-launch npx fetch
- [ ] 435 [P] - voice profile. **Blocked on Joe supplying real writing samples.**

### The three tips that matter

1. **Never let a session edit the hook currently guarding it.** Copy to scratch, test there, then
   install. A broken guard is silent. Phase 2 found this is sharper than it reads: a `settings.json`
   hook edit IS picked up mid-session for `Bash`/`PowerShell` matchers, contradicting what phase 1
   recorded, so a guard wired mid-run starts policing the very session that wrote it.
2. **One commit per todo, never batched**, so a revert is surgical. `/mega-todos` already does this.
3. **Verification cannot be "Joe reviews the diff."** Every phase needs a mechanical check, which is
   the whole reason phase 0 exists.

## Next up

**63 live todos, 295 in `done/`.** The harvest set above is ordered; the rest below is not.

A `/mega-todos` run on 2026-08-19 closed **33 todos in one pass**, 16 file-ownership lanes, one
commit per todo. Zero silent drops (reconciled as a set difference, not a count), zero barrier
failures, zero blocked builders. The full record is in each todo's own Notes line under `done/`.

Its own wrap-up then filed **twelve** new ones, which is the honest shape of a run that wide: three
lanes shipped something correct that was not wired up, because the wiring lived in a file another
lane owned.

- **481** - nothing checks a todo is filed in the repo it changes, and an autopilot run executed
  four commits into sibling game repos from a platform session because of it. Joe raised it
  2026-08-22; 479 below is the same defect in the other direction
- **479** - Obsidian daily-note automation (screenpipe pipe) is a month stale; re-filed here
  from zng-app's backlog 2026-08-22, it was global tooling sitting in a project repo
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

The session's own `/close` then added three more:

- **403** - `**Origin:** dev`. Reopen the comment rule from what comments are actually WORTH, in a
  dedicated `/brainstorm` session. Joe does not value comments for their own sake, does not care how
  they look in his own repos, does care about noise in client repos, and wants to know what a comment
  buys an AI reader. **399 is gated on this** and may be closed by it.
- **404** - nothing mechanically stops a subagent writing into `.claude/todos/`, and one did (391).
  Carries forward the doctrine's own earlier rejection of a write-guard hook, plus the new evidence
  that the report-back channel it relied on was bypassed.
- **405** - `/mega-todos` Step D places its verify barriers inside the Workflow script, which has no
  shell access, so they cannot run there. Same shape as 347, 358 and 369.

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
  command-chaining detector flagged 55 percent of 30047 real commands. Todo 416 deleted all three
  prototypes on 2026-08-20; the measurements live in `done/270`, `done/308` and `done/311`, and each
  of those notes says a revisit would not reuse the code.
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
