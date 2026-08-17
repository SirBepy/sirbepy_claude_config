---
name: auto-do-todos
description: Autopilot for the todos backlog. Grinds every todo it can decide on its own via bounded /iterate-it, asks only when there is nothing left it can decide, and parks the rest as questions in the todo files for the next run.
disable-model-invocation: true
---

# /auto-do-todos

> `/autopilot` pointed at `.claude/todos/`. Decide everything you can decide, never stop mid-run to
> ask, and turn the things only the dev can answer into questions the NEXT run opens with.

**Trigger:** `/auto-do-todos` only. Never auto-invoke.

## Sidebar badge

`<cc-autopilot:on>` and `<cc-autopilot:off>` drive the "autopilot" badge on the session row in the
sidebar, same markers `/autopilot` uses, and are stripped from the rendered chat. Step 1 and Step 9
below are the only place they get emitted; this section documents what they do, it is not a second
instruction to emit them.

## Precedence

For the duration of an **unattended** run (the default - see Attended mode below) this contract
**SUPERSEDES** the global "front-load all questions before starting" rule and every nested skill's
`AskUserQuestion` step. Step 5 is the run's compliance with that global rule: it is the ONE question
round, it happens before any HARD todo executes, and after it the run does not ask again.

An **attended** run does not supersede that global rule - it restores it. See Attended mode for what
that changes in Steps 5-7.

Everything else stays in force: CLAUDE.md, `/commit` only (never raw `git commit`), auto-commit on
qualifying turns, and every Hard Stop in `/autopilot`.

## Adopted contracts (referenced, not restated)

- `~/.claude/refs/delegation-doctrine.md` in full - 90/10 rule, scout spec packs, the verbatim
  stage-don't-commit line in every dispatch, orchestrator hygiene, report quality tells.
- `/autopilot`'s **behavior contract** in full - tiered uncertainty resolution, BOUNDED
  `/iterate-it` (`--explore-max=2 --polish-max=1`, max 3 escalations per run), nested-question
  suppression including the ship/another-round/abandon special case, verify-before-done.
- `/autopilot`'s **3-strike runaway guard** - the same verification failing 3x consecutively, or a
  todo making zero forward progress across 3 consecutive subagent dispatches, parks that todo and
  the run continues with the next one. No infinite retry.

Two deliberate divergences from `/autopilot`, both chosen by the dev on 2026-08-04:

1. **Context thresholds are 30% / 40%**, not autopilot's 50% / 60% (see Step 6).
2. **No `.for_bepy/autopilot-logs/` channel.** A genuine blocker or a dev-only fork does not get a
   log file nobody reads - it gets written back into its own todo as an `## Open questions` block
   (Step 8), which the next run surfaces at the very start.

There is no `--sleep` flag. Chain `/sleep-when-done` yourself if you want it.

## Cleanout intent

If the prompt that invoked this run asks to drop, clear out, prune, or clean up the backlog (not
merely to run the skill), the run is in **cleanout mode** for its duration:

- Step 2's `/cleanup-todos` keep-all auto-resolve is SUSPENDED. Every drop/archive/merge candidate
  it finds, `ai`-origin included, carries into Step 5's question round instead of being silently
  archived or silently carried forward.
- Step 5 fires unconditionally, up front, before any todo executes, carrying that full candidate
  list alongside its normal triggers.

Bare invocation (no cleanout phrase) is unaffected: Step 2 keeps today's no-confirm auto-archive for
`ai`-origin candidates.

## Attended mode

**Trigger.** The prompt that invoked this run explicitly invites questions mid-run - phrasing like
"feel free to ask", "ask me anything", "ask whenever". Detected once, from the invoking prompt text,
at Step 1. No flag to remember, no mid-run re-check. Absent that phrasing, the run is unattended and
every step behaves exactly as written elsewhere in this file - this section changes nothing for it.

Attended mode restores the global "front-load all questions" rule for the run (Precedence's
supersede clause does not apply) and changes three steps:

- **Step 5** loses its one-round cap - it still fires under its normal trigger, but does not close
  the door after.
- **Steps 6 and 7** may ask, narrowly: only for a fork that genuinely blocks the todo in hand, never
  for something Step 8 could park instead. Unattended, both keep their "never ask" promise exactly
  as written in those steps.
- A question the dev answers with a request for explanation, or a follow-up question, is a normal
  turn, not a second round - budget for it rather than treating the round as spent.

Cleanout mode and attended mode are independent and may both be active in the same run.

## Order of operations

1. Record `START_SHA` (`git rev-parse HEAD`) - Step 9 diffs against it, then end this first response with `<cc-autopilot:on>` on its own line, nothing after.
2. `/cleanup-todos`, unattended - always runs (Steps 2-3).
3. `/batch-todos`, unattended, unless Step 2 left nothing EASY - its EASY batch executes here.
4. Triage the remaining queue into AUTO and DEV (Step 4).
5. The one question round, if it triggers (Step 5).
6. Grind the AUTO queue (Step 6).
7. Second-pass escalation if the AUTO queue empties with headroom left (Step 7).
8. Park every unresolved DEV fork into its todo (Step 8).
9. Wrap-up verification, then the written summary. Emit `<cc-autopilot:off>` (Step 9).

## Steps 2-3 - Nested skills run unattended

Both `/cleanup-todos` and `/batch-todos` have an "Unattended runs" section. A `/auto-do-todos` run
IS an unattended run, so:

- `/cleanup-todos` still prints its full report. Its own origin rule then applies unchanged:
  `ai`/absent-origin todos that are dead, duplicate or not worth doing ARE archived, with no confirm
  gate - that gate never existed for them. Only `dev`-origin candidates carry into the Step 9 summary
  as still-pending. **In cleanout mode (see above), skip this auto-resolve entirely** - every
  candidate, `ai`-origin included, carries into Step 5 instead of being archived or carried silently.
- `/batch-todos` still prints its dry-run report, then proceeds as though the dev replied `run it`.
  Its Step 5 `FLAG` verdicts still re-queue as HARD rather than being auto-answered.

Do not wait for a reply at either gate.

**When each step runs.** Step 2 runs on every run by default: `/cleanup-todos` is the only pass that
dedupes, re-verifies premises against the tree, and archives dead `ai`-origin todos. Step 3 is
skipped when Step 2 leaves no unclaimed EASY todo, since Step 6 grinds that same queue directly and
a second nested dry-run report adds nothing. Cleanout mode always runs both.

**Two invocations move Step 2's work rather than skipping it.** Both were real runs improvising
against a rule that used to read "no size exemption"; the substitution is sanctioned now, the
guarantee is not negotiable.

- **Questions-first invocation** - the prompt demands the dev's input be gathered before any work
  ("see if any of them require input from me, and only then do anything"). `/cleanup-todos` and
  `/batch-todos` both DO work, so running them first disobeys the prompt. Order it like cleanout
  mode instead: Step 4's triage runs first over every todo in full, then Step 5, then Steps 2-3
  fold into Step 6's grind. The triage prompt MUST then carry Step 2's three unique functions as
  explicit requirements - dedupe across the whole backlog, re-verify each premise against the tree,
  and flag dead `ai`-origin todos for archival - because nothing else in the run provides them.
- **Named-subset invocation** - the dev names the exact todo ids to run ("auto-do-todos those 5").
  The queue is given, so Steps 2-4 have nothing to select and are skipped; the run starts at Step 6
  over the named ids. Backlog-wide dedupe and dead-todo archival are NOT performed, and the Step 9
  summary says so rather than implying the backlog was swept.

Any other substitution for Step 2 is still a deviation. Report it in Step 9 rather than performing
it silently.

## Step 4 - Triage into AUTO and DEV

Dispatch ONE subagent (`model: 'sonnet'`) with the full text of every todo `/batch-todos` parked as
HARD. Per todo it returns:

- `bucket`: **AUTO** or **DEV**.
  - **AUTO** - no dev decision is genuinely required. This INCLUDES real design/architecture
    judgment calls, which a bounded `/iterate-it` converges on its own. The bar for AUTO is not
    "obvious", it is "a competent agent can reach a defensible answer without the dev".
  - **DEV** - a genuine fork only the dev can settle: personal taste with no defensible default
    (unit preference, which of three equally-valid interaction models he wants), a hard stop from
    `/autopilot`'s list (credentials, destructive/irreversible, physical action), or a decision
    whose blast radius is large and hard to reverse.
- If **DEV**: the exact question(s), each tagged `[UX]`/`[ARCH]`/`[SEC]`/`[DATA]`/`[TOOLING]`, with
  2-4 concrete options and a recommendation where one exists.
- `priority`: High/Med/Low.

**Lean AUTO, not DEV.** The old version of this skill defaulted to DEV when in doubt and ended up
refusing to touch most of the backlog. Mark DEV only when you can name why a defensible answer is
impossible without the dev - "it's a design decision" is not a reason, that is what `/iterate-it`
is for.

Also scan every todo for an existing `## Open questions` block written by a previous run. Those are
pre-crystallized DEV questions and they feed Step 5 directly, no re-derivation.

## Step 5 - The one question round

**Trigger.** Run this round if and only if EITHER:

- the AUTO queue is **empty** - there is nothing to grind, so asking is the only way to make
  progress; or
- one or more todos carry a pre-written `## Open questions` block from a previous run - the dev
  already knows those are coming and asked for them to be opened with; or
- the run is in **cleanout mode** (see above) - fires immediately, up front, before any todo runs.

Otherwise **skip this step entirely**, grind the AUTO queue, and let Step 8 park the DEV forks for
next time. A run that has real work to do never interrupts the dev.

**Shape.** Keep it quick - the dev's words are "ask me quick and then we done":

- Highest priority first, `AskUserQuestion` only, 4 per call, chain past 4.
- **Cap the round at 8 questions (2 calls) when using the builtin `AskUserQuestion`.** When an
  uncapped equivalent is available in this session (e.g. `mcp__cc_conductor__ask_user_question`,
  documented as having no cap), ask everything in that one call instead - the 8-cap exists only
  because the builtin tool stops at 4 per call, not as a limit on how much a run may resolve.
  Anything still unaddressed after the round stays parked via Step 8.
- Every question carries a final **"you decide - autopilot it"** option, so any question the dev
  does not care about is handed straight back to bounded `/iterate-it` at zero cost to him.
- Every question carries a **"stop here"** escape so he can end the round without answering the
  rest; unanswered questions park via Step 8.

Answered todos move into the AUTO queue. Unattended, this is the run's ONLY question round - Steps 6
and 7 never ask, no matter what they find. Attended, this round still fires under the same trigger,
but is not the last one - see Attended mode.

## Step 6 - Grind the AUTO queue

High to Low priority. Independent todos may fan out concurrently per the doctrine's Parallelism
rule, but `refs/delegation-doctrine.md`'s "Liveness and session budget" section governs that fan-out
- it names the concrete dead-dispatch check and caps width by session budget, not context%. A
healthy context reading does not mean a fan-out is safe.

Any fan-out covering more than one todo also follows the doctrine's "Fan-out reconciliation"
section: diff the union of ids assigned across the fan-out against the AUTO queue before dispatch,
then diff reported ids against it after return - a set difference, never a count.

Per todo:

1. Claim it per `close/ai-todos-format.md`.
2. Execute via a subagent under the adopted contracts above. Heartbeat the claim at checkpoints.
3. `~/.claude/skills/close/complete-todo.ps1 -Id <id> -Note "<what happened>"` - one call records
   the Notes line, archives it, prunes its PLAN.md line, and releases the claim.
4. `/commit` - invoke and read the skill in full only for this run's first commit; every commit
   after that follows `/commit`'s procedure directly (session marker already written, prefilters,
   pathspec form, branch/overlap checks all still apply) without re-invoking the skill file.
5. Run `node ~/.claude/skills/context-left/context-left.mjs` and read pct used.
   - **>= 40% used (HARD_STOP_AT):** stop taking new todos immediately, even with queue left, and
     go to Step 8.
   - Otherwise: next todo.

A todo that hits the 3-strike guard or a Hard Stop mid-execution: release its claim, leave the todo
in the backlog, record why for Step 8, and continue with the next todo - unless the run is attended
and the block is a genuine dev-only fork, in which case ask once inline (see Attended mode), then
resume the todo with the answer. Never let one todo end the run.

**A fan-out that dies mid-edit with no report** (session limit hit, silent stall): do not resume
blind. Follow the doctrine section's recovery - reconstruct state from `git status` plus a real
lint/test run, label every reconstructed verdict INFERRED rather than reported, release every claim
those todos held, and write the handoff into Step 8 before taking any new todo.

Queue empties before 40%? Go to Step 7.

## Step 7 - Second-pass escalation

The AUTO queue is empty and there is headroom left. Read ctx used again.

- **>= 30% used (SLOW_AT):** go to Step 8. Do not start anything new.
- **< 30% used:** re-triage the DEV set ONCE, with a stricter bar: for each todo, ask whether a
  bounded `/iterate-it` really cannot reach a defensible answer, or whether it was bucketed DEV out
  of caution. Whatever downgrades to AUTO goes through Step 6's loop. Whatever survives a second
  look as genuinely dev-only stays DEV.

This step is where the old skill asked more questions. Unattended, it still doesn't - it tries harder
instead. Attended, a fork that survives re-triage as genuinely dev-only may ask once inline (see
Attended mode) rather than falling through to Step 8. Re-triage runs at most once per run.

## Step 8 - Park what is left

For every todo still in the backlog carrying an unresolved DEV fork, a hard-stop blocker, or a
question that overflowed Step 5's cap, edit its file to carry (or refresh) an `## Open questions`
section, placed after `## Acceptance`:

```md
## Open questions

Written by /auto-do-todos on <YYYY-MM-DD>. The next run opens with these.

- [ ] [UX] <question> - options: <a> / <b> / <c>. Recommended: <b>, because <one line>.
- [ ] [ARCH] <question> - options: ... Recommended: ...
```

Rules:

- One checkbox per question, domain-tagged, options inline, a recommendation whenever one exists.
- A blocker needing the dev's physical action (credential, hardware, destructive op) is written the
  same way, phrased as what he has to do, not as a choice.
- Refresh an existing block rather than stacking a second one; drop questions the run answered.
- This section is this skill's own addition to `close/ai-todos-format.md`'s shape. It is greppable
  on purpose - Step 4 reads it back on the next run.
- Never write git instructions into a todo, per the contract's off-limits rule.

## Step 9 - Wrap-up verification and summary

Dispatch subagents to verify the run's whole diff (`git diff START_SHA..HEAD`):

1. `/code-check START_SHA..HEAD` - structural + convention review, writes findings to the backlog.
2. The project's fast-check floor (typecheck, unit tests, lint, build) - whichever it actually has.
3. E2E if the project has a runnable suite (`test-flow`, `flutter-e2e`, an existing
   Playwright/Cypress config) - best effort, skip with a one-line note if there is no headless way.

Also drain every builder's "Out-of-scope findings" section gathered during Step 6: the orchestrator
files each one as a properly allocated todo, `**Origin:** ai`, per `refs/delegation-doctrine.md`'s
"Out-of-scope findings" section - never the builder itself.

Fix anything trivial and re-verify inline, then `/commit`. Anything else found becomes an
`## Open questions` entry or a new todo - never a mid-run question. A new todo filed here is a
verification finding Claude made on its own: `**Origin:** ai`.

Then the written summary: todos completed with commit shas, todos parked and why, every fork the run
auto-decided and what it picked, questions asked and answers applied, `/cleanup-todos`'s still-pending
dedupe/drop candidates, final ctx% used, and the verification result (code-check finding count,
test/e2e pass-fail), immediately followed by `<cc-autopilot:off>` on its own line, nothing after.

## Notes

- Never invoke `/autopilot` as a literal slash command - this skill ADOPTS its contract by
  reference (see above) and layers the backlog-specific flow on top, the same way `/delegate` does.
- Never commit directly. `/commit` is invoked and read in full once per run; every completed todo's
  commit after that follows its procedure directly, same cadence as `/batch-todos`.
- Source of truth for the backlog: `.claude/todos/` per `close/ai-todos-format.md`.
- Thresholds live in Step 6 (`HARD_STOP_AT = 40%`) and Step 7 (`SLOW_AT = 30%`) - tune there.
