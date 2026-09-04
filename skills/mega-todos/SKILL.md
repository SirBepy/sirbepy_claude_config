---
name: mega-todos
description: Wide parallel backlog burn-down. Drives .claude/todos/ through the Workflow tool - many builder agents at once in file-ownership lanes, each committing its own todo via an injected /commit procedure, with tiered verification barriers. The heavy sibling of /auto-do-todos.
disable-model-invocation: true
---

# /mega-todos

> `/auto-do-todos` was capped by the MAIN THREAD's context, not by agent capability. This skill moves
> the whole grind into a Workflow script so the main thread only ever holds lane assignments,
> barrier results, and the summary.

**Trigger:** `/mega-todos` only. Never auto-invoke.

## Relationship to `/auto-do-todos`

`/auto-do-todos` stays as the CHEAP sequential mode for a small backlog. This skill is the wide one.

Steps 2-5 of `/auto-do-todos` are **adopted by reference, not restated**: `/cleanup-todos`
unattended, `/batch-todos` unattended, the AUTO/DEV triage with its lean-AUTO bar, and the one
question round with its question-cap logic (capped at 8 for the builtin `AskUserQuestion`, uncapped
when an equivalent like `mcp__cc_conductor__ask_user_question` is available). Read that file and run
those steps as written. Triage logic lives in exactly one place so the two skills cannot drift.

Everything from Step 6 onward is replaced by this file.

## Also adopted

- `~/.claude/refs/delegation-doctrine.md` in full, with ONE deliberate override: the verbatim
  stage-don't-commit line is replaced by the injected commit block below. Every other clause holds -
  scout spec packs, orchestrator hygiene, report quality tells, the no-`run_in_background` rule.
- `/autopilot`'s behavior contract: bounded `/iterate-it`, nested-question suppression, the 3-strike
  runaway guard.
- `~/.claude/refs/process-hygiene.md` for anything spawning Node.
- `~/.claude/skills/pickup/SKILL.md` Step 4's timed-out-card branch, for any question a lane's
  builder or the Step C scout raises mid-run that goes unanswered - its reversibility gate is what
  covers a fork raised mid-run, not just autopilot's known-at-triage forks.

## Sidebar badge

Emit `<cc-autopilot:on>` at the end of the first response, `<cc-autopilot:off>` at the end of the
final one. Same markers `/autopilot` uses.

## Prerequisite: explicit opt-in

The Workflow tool spawns dozens of billed agents and requires the dev's explicit request. Typing
`/mega-todos` IS that request; no separate confirmation is needed. But if the Workflow tool is
unavailable in this session, do NOT silently fall back to sequential dispatch pretending to be this
skill - say so and offer `/auto-do-todos` instead.

## Order of operations

1. Preflight (Step A) - record `START_SHA`, verify the repo's commit preconditions, emit
   `<cc-autopilot:on>`.
2. `/cleanup-todos` and `/batch-todos`, unattended, per `/auto-do-todos` Steps 2-3.
3. Triage and the one question round, per `/auto-do-todos` Steps 4-5.
4. Exclusion pass (Step B) - drop what must not be automated.
5. Lane assignment (Step C) - a scout partitions the AUTO queue by file ownership.
6. The workflow run (Step D) - lanes execute in parallel; the main thread verifies at each barrier
   between batches, since a Workflow script cannot run a shell command.
7. Archival and wrap-up (Step E).

## Step A - Preflight

Record `START_SHA` (`git rev-parse HEAD`) and `EXPECTED_BRANCH` (`git rev-parse --abbrev-ref HEAD`).
`EXPECTED_BRANCH` is substituted into every builder's branch guard, so a peer session moving HEAD
mid-run stops the agents instead of scattering commits onto someone else's branch (see
`.claude/todos/done/55-commit-must-recheck-branch-before-each-commit.md`; a long wide run is the worst
case for that hazard). Then verify, in the target repo, the five conditions the injected commit block
depends on. Each is a one-line check and each has a defined consequence:

| Check | If present | Consequence |
|---|---|---|
| `GIT_FLOW.md` at repo root **AND** HEAD is a protected-trunk name (`main`/`master`/`develop`) **AND** the repo has a remote | branch-protection fires | agents would each stall on `AskUserQuestion`. **Abort the run** and tell the dev to branch first. |
| `.claude/commit-style.md` | overrides prefixes/grouping | read it once and paste its rules INTO the injected block. |
| `.claude/skills/run-tests/SKILL.md` | `/commit` step 6 | 45 agents would each run the full suite. Strip step 6 from the injected block; the barrier runs it once instead. |
| `list_peers` shows another session | shared tree | post once from the main thread naming the whole run's scope, then let agents skip their own peer check. |
| `core.hooksPath`'s `pre-commit` hook invokes `lint-staged` | stash race | switch `COMMIT_MODE` to `barrier` (see below) instead of the injected per-builder commit block. |

All three conditions must hold together, mirroring `/commit` step 1a's real gate rather than a loose
proxy for it. `GIT_FLOW.md` alone is harmless on a feature branch, and treating it as sufficient
bricks the skill in every repo that documents its git flow, which is most of them.

**`COMMIT_MODE` default is `per-builder`** (the injected commit block below). It switches to
**`barrier`** when the hooksPath check above fires: `lint-staged@16` stashes unstaged changes before
running its tasks, and with N agents holding uncommitted work in one tree that stash/restore cycle
can swallow another agent's in-flight edits - not theoretical, 6 of 19 commits hit this race on
2026-08-11. In `barrier` mode, builders never touch git - they leave every change unstaged - and the
main thread commits by pathspec at each barrier instead. `git commit -m "..." -- <pathspec>` builds
a TEMPORARY index for that one command, so the hook only ever sees the pathspec's files and never
the shared index; a pathspec commit of files lint-staged doesn't match is a complete no-op for it.

Also confirm the working tree is clean of other people's uncommitted work (`git status`). A wide
parallel run over a dirty shared tree is how another session's work gets swept into a pathspec.

## Step B - Exclusions

Remove from the AUTO queue, regardless of what triage said:

- **Anything targeting the global `~/.claude` tree, WHEN this run is in a project repo.** Global
  CLAUDE.md forbids doing global work from a project session. Those belong in `~/.claude`'s own
  backlog and are not a project run's business.
  **Does not apply when the target repo IS `~/.claude`.** Read literally without this carve-out the
  rule excludes the entire backlog and the run has nothing to do, since every todo in that repo
  targets the global tree by definition. Invoking `/mega-todos` while in `~/.claude` is the dev
  saying so in that session, which is exactly what CLAUDE.md's rule asks for.
- **`live-verify` / `verify ... live` todos, but only the ones that actually need it.** A green
  verify floor cannot see "this looks wrong" (delegation doctrine, Visual work), but most todos
  titled that way just want a picture, not a running binary. Before excluding one, name which
  concrete blocker applies - a title match alone is not a reason:
  - real hardware (a phone, another OS)
  - a real backend process or a real streamed turn
  - an OS-level capture (crash log, process trace, cold boot)
  - the dev's own taste, or his installed build specifically
  If the project has a way to render a view without its real backend (a harness, a story, a preview
  route), use it and queue the todo AUTO with a capture step instead of excluding it. First check
  the project's spec directory for a name match too - grep it for the todo's feature name; if an
  existing spec already answers the question, that is also not an exclusion, it is a done-without-
  building. Measured 2026-08-22 in `claude_usage_in_taskbar`: 24 todos were dropped on title alone,
  and a re-triage against the real harness found 8 fully reachable, 10 partially, and 4 already
  answered by specs nobody had connected - only 6 were genuinely dev-only.
- **Anything a Hard Stop covers:** credentials, destructive or irreversible ops, physical action.
- **Todos whose fix is a UI/visual judgment call** with no approved mockup to match.
- **Anything already claimed in `.claude/todos/.claims/`.** Another session is executing it right
  now. A run this long outlives a single snapshot, so re-read the claims directory at every barrier
  and drop newly-claimed todos from lanes that have not started yet - a claim appearing mid-run means
  a peer took it while we were building.

Report every exclusion in the Step E summary with its own reason, e.g. "2 need a real device, 1
needs a Mac, 3 need a real daemon turn" - never a bare count like "24 live-verify". A count is
unfalsifiable; a reason per todo is reviewable, and a wrong one is visible. Never drop silently.

## Step C - Lane assignment

This is the step that makes parallel commits safe, so it is not optional and not eyeballed.

Dispatch ONE read-only scout (`model: 'sonnet'`, `effort: 'high'`) with the full text of every AUTO
todo. It returns, per todo: the exact set of files the fix will touch (`file:line` where known), and
a one-paragraph spec pack a builder can act on without re-deriving the map.

**The scout MUST existence-check every path it returns** (`Test-Path` / `ls`) and mark each
`verified` or `unverified`, writing `NEW:<path>` for a file the fix creates. A path it cannot
resolve is reported `unverified`, never silently replaced with a plausible-looking one. Give the
scout an explicit tool-call and wall-clock budget and tell it to report partial work rather than
overrun: three scouts died silently mid-run on 2026-08-25 with no partial result, and a budgeted
replacement over the same material returned cleanly.

**Then the main thread re-checks the union of returned paths itself, in one batch, before any
dispatch.** One `ls` over the whole set costs nothing and does not depend on the scout cooperating.
This is the actual gate; the scout's own marking is the cheap first pass.

The main thread then partitions into **lanes** by the transitive closure of file overlap:

- Two todos sharing ANY file are in the SAME lane and run **sequentially** within it.
- Lanes share no files, so they run **in parallel** with no possibility of one agent's pathspec
  commit capturing another's half-written file.
- A todo whose file set the scout could not pin down goes in its own lane, alone. Never guess.
- **A todo with any `unverified` path does not dispatch at all** until that path is resolved by
  hand. A wrong file set means the builder cannot do its job and the lane map was computed from
  fiction: 5 of ~30 dispatches in the 2026-08-20 run hit one, including an owned file that did not
  exist.

Expect the backlog's structural cluster (the daemon-link / `main.ts` / `bootstrap.rs` split-and-dedupe
todos) to collapse into a few large lanes. That is correct and is the honest ceiling on parallelism:
**lane count, not agent count, is what bounds concurrency.** The harness independently caps
concurrent agents at `min(16, cores - 2)` regardless.

### The trust-boundary pass - a second partition, not an optional one

File overlap answers "can these two agents write concurrently". It does NOT answer "do these two
agents share a security invariant", and two modules can be file-disjoint while sharing a threat
model. So after the file partition, sweep the AUTO queue again asking: do any two todos touch the
same trust boundary? A network-reachable allowlist, an auth check, a permission gate, or a path/id/
handle accepted from a client all count.

Where two do, pick one:

- put them in the SAME lane with an explicit "apply the same guard as its sibling, named here" line
  in both briefs, or
- write the specific guard verbatim into BOTH briefs.

**Never resolve it by telling one brief to "follow the pattern the other one established".** That is
the exact wording that failed. Worked example, run of 2026-08-12: todos 434 and 244 both added daemon
RPC modules taking a client-supplied filesystem path, both landed in the same `SAFE_METHODS`
allowlist, same lane, sequential, and 244's brief said to follow 434's pattern. 244's agent added an
`is_known_cwd` guard; 434's did not, leaving `remove_worktree` remotely callable with an arbitrary
path. 244 even documented the divergence in a doc comment. Nobody read it, because a doc comment is
not a gate. `/code-check` caught it afterwards; no barrier did.

Add one barrier line item for the same class: **for any todo that added an entry to a remote-callable
allowlist, diff its input validation against the sibling entries already in that list.**

Before Step D dispatches, reconcile the lane map per `refs/delegation-doctrine.md`'s "Fan-out
reconciliation": diff the union of ids across every lane against the AUTO queue - a set difference,
never a count. An id in neither means a todo was dropped from partitioning, not that it is done.

`log()` the lane map at run start so the dev can see the shape.

## Step D - The workflow run

Author the script inline. Shape:

- `pipeline()` over LANES, never over todos. Each lane's stage runs its todos in sequence inside one
  agent call chain, so ordering within a lane is guaranteed.
- One builder agent per todo, `model: 'sonnet'`, `agentType` default. Tune `effort` down for
  mechanical splits, up for anything with judgment.
- Barriers do NOT live in the script. **A Workflow script has no shell and no filesystem** - its only
  primitives are `agent()`, `parallel()`, `pipeline()`, `log()`, `phase()` and `workflow()` - so a
  barrier that runs `cargo check` or `pytest` cannot be a step in it. Return the workflow between
  batches and run the barrier in the MAIN THREAD, which is where Step E already has to archive from
  anyway. Do not spend a whole subagent per barrier just to run three commands.

**Verify ladder** (settled with the dev 2026-08-10; generalised 2026-08-12; thread ownership made
explicit 2026-08-25 per todo 405).

Defined by ROLE, not by command. Resolve each role to the project's real commands during Step A and
state them in the run's opening `log()`. A ladder whose roles cannot be filled at all is a **hard
stop** - a wide parallel run with no verify floor is 15 agents committing unchecked.

| Role | Runs on | When | Scope |
|---|---|---|---|
| **Cheap per-todo** | the builder agent | before it commits | only what that agent touched |
| **Per-batch barrier** | MAIN THREAD | every batch | repo-wide, must stay fast enough to run often |
| **Full floor** | MAIN THREAD | every 10-15 completed todos | everything, including tests and e2e |
| **Final barrier** | MAIN THREAD | once, at run end | see the rule below |

Only the per-todo rung belongs to a builder, because a builder is a real agent with real shell
access. Every other rung is the main thread's, between workflow invocations.

**In `barrier` COMMIT_MODE (Step A)**, the per-batch and full-floor barriers each additionally
perform the commit step before their verify commands run - see "Barrier COMMIT_MODE" under the
injected commit block below. Builders never commit in this mode; the main thread does, once per
completed todo, in lane order.

**The final-barrier rule, stated so there is no todo-count ambiguity:** the last barrier of a run is
the **cheap per-batch check**, NOT the full floor - unless the full floor has not run for 10 or more
completed todos, in which case run it once at the end. "This is the last barrier, so do the thorough
one" is a natural misread and it is wrong. Measured cost of that misread, 2026-08-11: a 7-todo run
took 94 minutes wall clock, of which the builders were 6 minutes and the barrier was ~65. The
correct barrier was ~10.

**Full-floor commands rarely share build artifacts.** `cargo check --all-targets`, `cargo test --lib`,
`cargo test --test <name>` and `cargo build` produce different artifact sets - `check` emits no codegen
`build` can reuse - so running all four serially costs roughly four builds of the tree, not one build
plus increments. If a test run and a build are both genuinely wanted, prefer `cargo test --lib` alone,
which already compiles the lib. A passing `cargo check --all-targets` has already proven every target
compiles.

**Rust: always `--all-targets`, never bare `cargo check` or `cargo build`.** Neither compiles
`#[cfg(test)]` code, so both report an import used only by tests as unused. Acting on that warning
deletes a live import and breaks the test build with every check still green - which is exactly what
happened on 2026-08-12.

Worked examples, one per stack shape:

- **Rust / Tauri** - per-todo: nothing, cargo is too slow to run per todo. Barrier:
  `cargo check --all-targets --manifest-path src-tauri/Cargo.toml` plus `pnpm tsc --noEmit`.
  Full floor: `cargo test --lib`, plus e2e if headless.
- **Frontend (React/Vite)** - per-todo: `npx tsc --noEmit` plus the relevant vitest file. Barrier:
  `npm run lint` repo-wide. Full floor: `npm run test` and `npm run build`.
- **Docs / scripts repo with no build system** (`~/.claude` itself is one) - per-todo: syntax-check
  only the files touched. Barrier, repo-wide: `python -m py_compile` over `hooks/*.py`, `node --check`
  over changed `.mjs`/`.cjs`, and PowerShell parse via
  `[System.Management.Automation.Language.Parser]::ParseFile` over changed `.ps1`. Full floor: the
  same, plus resolving every `~/.claude/...` path referenced by a changed markdown file to confirm it
  exists. There is no compiler here, so a broken cross-reference IS the failure mode that matters.

**A barrier failure is fixed forward, never reverted.** Other sessions share this tree and this
branch; `git revert` / `git reset` on master is the one thing guaranteed to hurt someone else's work.
Dispatch a repair agent scoped to the failing lane, and if it hits the 3-strike guard, park the todo
and note the broken commit in the summary.

Return from the script only condensed data: per todo the id, what changed, its commit sha, and
pass/fail. Never file bodies, never transcripts.

## The injected commit block

This is the deliberate divergence from the delegation doctrine. `/commit` is pure procedure - git
commands, one awk prefilter, and a marker file - so it CAN be followed by an agent that cannot invoke
skills. Paste the full `refs/builder-preamble.md` block first (unmodified, including its screenshot-id
paragraph and its `run_in_background ... FORBIDDEN` line - those two are hook-enforced markers, see
that file's own note), then append this block verbatim when `COMMIT_MODE = per-builder` (Step A) -
see "Barrier COMMIT_MODE" below for the `barrier` case. Substitute `<EXPECTED_BRANCH>` from Step A;
leave `<FILES>` as-is, the agent fills that with its own owned paths.

Prefer `skills/mega-todos/build-dispatch.ps1` over hand-pasting either block: it reads both this file
and `refs/builder-preamble.md` off disk and emits the finished prompt from `-Owned`, `-OffLimits`,
`-Task`, `-CommitMessage` and `-ExpectedBranch`, which is what closes the drift risk (`bdb0323`)
retyping created.

The opening two lines below are load-bearing, not decoration: `hooks/dispatch-preamble-guard.py`
hard-requires the literal staging sentence somewhere in the prompt, and this skill's whole point is
that the builder commits, so the honest move is to quote the normal-case sentence and then say
plainly that this dispatch is the documented exception - never silently drop it or invent a
different phrasing, both were tried and both either got rejected or misled the builder:

```
A normal dispatch says: "Stage your changes but do NOT commit." THIS DISPATCH IS THE DOCUMENTED
EXCEPTION - see the COMMITTING section below.

COMMITTING IS PART OF YOUR JOB. You cannot invoke /commit as a skill, so follow this procedure
exactly. Do not improvise around it and do not skip a step because the change looks small.

Commit as soon as this work is gated, before you write your report-back. A builder that commits
first keeps its work through a session-limit kill or a process exit; one still composing its report
when the kill lands loses everything even if the diff was finished - confirmed twice, 2026-08-31 and
2026-09-02.

1. A global PreToolUse hook BLOCKS raw `git commit`. Immediately before EVERY commit, write a fresh
   marker IN ITS OWN TOOL CALL, never chained with the commit (`;`/`&&`) - the hook inspects the
   whole command string BEFORE any of it runs, so a chained marker is always rejected whole (the
   hook needs one written within the last 2 minutes, and consumes only the oldest, so concurrent
   agents do not steal each other's):
   Set-Content -Path "C:\Users\tecno\.claude\hooks\.commit-marker-$([guid]::NewGuid().ToString('N'))" -Value "x"

2. Run `git status`, then `git diff -- <FILES>` (the working-tree diff check from `/commit` step 8).
   Account for every hunk shown. An unrecognised hunk - one you did not write this session - is a
   STOP: drop that path from `<FILES>`, name it in your report-back, and continue with the rest of
   your files. Drop, never stop-and-report-nothing - one shared file should not stall an otherwise
   clean lane in a run this wide. Never assume a dirty file in `<FILES>` is dirty only because of
   you - a pathspec commit takes a file's entire working-tree state, and `git status`'s one `M` line
   cannot tell you whose lines are in it.

3. Run the prefilter gate against exactly the paths you are about to commit, replacing <FILES>.

   Run it via Bash, never pasted inline: a bare `$0` in a skill's own body gets rewritten by
   skill-argument substitution, which is exactly why these live in scripts on disk. The path below
   is absolute on purpose - your repo root is NOT `C:\Users\tecno\.claude`, so a repo-relative path
   would silently fail to resolve here. Use the gate, never the three wrapped scripts directly - it
   resolves each FILES path's own repo independently, so a submodule path is read correctly instead
   of silently no-op'ing against the parent's index (todo 412):

   bash "C:/Users/tecno/.claude/skills/commit/prefilter-gate.sh" <FILES>

   Exit 1's labeled sections do NOT all get the same treatment:

   - comment-noise: if it prints anything, TRIM those blocks to the cap (2 lines typical, 4 hard per
     block) before committing. Do not ask, just trim. `comment-noise.sh` already excludes any flagged
     line byte-identical to a HEAD line under a different path, so a verbatim code move never reaches
     this report and needs no manual `git show` confirmation - whatever it does print is newly
     authored comment, which the cap exists to catch.
   - em-dash: fix the flagged added lines now, same do-not-ask treatment as comment-noise.
   - comment-tense: rewrite the flagged comment to state what the code IS, not what changed about
     it, same do-not-ask treatment. The gate runs this one too, so you can see its section here.
   - secret-scan: a hit STOPS YOU. Never auto-fix it and never commit around it - a hardcoded
     credential needs a human decision. Leave your work uncommitted and report the hit, naming the
     file, in your report-back.

   Exit 2 is NOT a finding - it means the gate could not run (bad path, no repo found). It prints one
   plain `ERROR:` line. Fix the invocation and rerun; never treat it as a prefilter hit.

4. `git add` any UNTRACKED file you created, by name. Tracked files need no add.

5. BRANCH GUARD, immediately before every commit. Run `git rev-parse --abbrev-ref HEAD`. If it is
   not `<EXPECTED_BRANCH>`, or if it prints `HEAD` (detached), STOP: do not commit, and report the
   branch you saw. Another session sharing this checkout can move HEAD mid-run, and pathspec commits
   protect the INDEX, not the BRANCH - the two hazards look alike and only one is handled for you.

6. Commit BY PATHSPEC, naming every one of your paths:
   git commit -m "<PREFIX>: <title>" -- <FILES>
   This form commits those paths' working-tree state and never reads the index, which is what makes
   it safe while other agents work in this same tree.

HARD RULES, no exceptions:
- Commit ONLY files assigned to you. Another agent owns every other file in this repo right now.
- NEVER `git add -A`, NEVER `git commit -a`, NEVER a bare repo-wide pathspec.
- NEVER `git stash`, `git reset`, `git checkout`, or `git revert` on ANY path. To see clean state,
  use `git show HEAD:<file>`.
- NEVER bump a version. Plain commit only, no `v` / `bump` / `push` variant. Do not push.
- Do NOT touch `.claude/todos/PLAN.md` or move anything into `.claude/todos/done/`. The orchestrator
  archives todos in a barrier; editing PLAN.md from a parallel agent clobbers other agents' edits.
- One purpose per commit. Prefix from: FEAT, FIX, REFACTOR, CHORE, DOCS, TEST, STYLE, DATA.
- No commit body unless something genuinely needs explaining. Never add AI attribution.
```

### Barrier COMMIT_MODE

When Step A set `COMMIT_MODE = barrier` (lint-staged detected), builders never run steps 1, 4, 5, 6
above - only step 2 (diff review) and step 3 (the prefilter, carve-out included) as their verify
floor, then they report their finished paths without touching git. The main thread performs the
commit at each barrier instead, once per completed todo, in lane order:

1. Write a fresh marker (block's step 1).
2. `git add` any untracked file that todo's builder created, by name.
3. Run the branch guard (step 5).
4. Run the working-tree diff check again, right now, against the same `<FILES>` (step 2, above) -
   time has passed since the builder's own pass and another agent's commit may have landed in
   between. An unrecognised hunk is the same STOP: drop that path from `<FILES>` and name it in the
   barrier's own summary, then commit the rest.
5. `git commit -m "<PREFIX>: <title>" -- <FILES>` (step 6), naming that todo's files only.

Same HARD RULES apply, main thread substituted for builder throughout.

Alongside it, every builder prompt still carries the doctrine's full canonical preamble from
`refs/builder-preamble.md`, `<STAGING_LINE>` included as-is: in `barrier` mode the builder genuinely
never touches git, so "Leave all changes unstaged. The main agent will run /commit by pathspec after
your report-back." is simply true here, unlike in `per-builder` mode where the same line would be a
lie the injected block immediately overrides.

**The `<OFF_LIMITS>` list is load-bearing here in a way it is not in a normal dispatch.** In a
stage-only dispatch a stray edit is caught at review; here it goes straight into history. Name the
lane's owned files explicitly and state that everything else in the repo is another agent's.

## Retrying a killed wave

A wave dies two ways: an account session limit killing agents on dispatch, or the harness process
itself exiting before the workflow returns. Neither is total loss - see `refs/delegation-doctrine.md`'s
"Liveness and session budget" for how to tell a dispatch is actually dead rather than merely quiet;
do not re-derive that check here.

Before touching the lane map, triage per todo in this order - re-dispatching onto finished work is
the expensive mistake:

1. **`git log` first.** A todo whose builder committed is DONE regardless of whether a report ever
   arrived - drop it from the retry map entirely. When the report is missing, verify its
   `## Acceptance` block against the committed diff yourself; that verdict is a legitimate substitute
   for the agent's own.
2. **Then `git status` on the remaining lanes' owned files.** Anything dirty is that builder's
   partial work. Never assume it is correct just because it exists.
3. **Per partial, decide complete-and-verifiable vs genuinely half-done.** Complete-and-verifiable
   (a coherent, finished diff that simply never got committed) is cheaper to finish from the main
   thread: run the verify floor and commit it yourself instead of re-dispatching. Genuinely half-done
   (todo 794, 2026-09-02: one of two scripts converted, the shared helper created, the second script
   untouched) gets re-dispatched, with the partial state DESCRIBED in the brief and an explicit
   instruction to judge it rather than trust it - "THERE IS PRE-EXISTING UNCOMMITTED WORK IN YOUR
   OWNED FILES AND IT IS YOURS TO FINISH" is the phrasing that worked.

**`resumeFromRunId` only fits when the retry prompts are unchanged**, which the triage above usually
makes false. Resume replays completed agents from cache and re-runs only the failed ones with their
ORIGINAL prompts - it cannot inject the partial-work description above into a retry prompt, and a
prompt built for a clean tree is wrong once the tree is not clean. Author a fresh script instead,
once the lane map has been re-cut against the survivors. Build each retry prompt with
`skills/mega-todos/build-dispatch.ps1` (472) rather than re-pasting the preamble/commit block by
hand.

**If the workflow's own result is gone** (a process exit, or a task notification saying no
completion record was found), do not fall back to `git log` alone: read
`<transcriptDir>/journal.jsonl`, printed in the original Workflow tool result. It carries one
`{"type":"result"}` line per completed agent with that agent's full structured return - commit sha,
decisions made, unmet acceptance items, out-of-scope findings - even when the harness itself has
nothing. Recover reports from it before reconstructing from the tree alone.

## Step E - Archival, verification, wrap-up

Archival is **main-thread only**, because `complete-todo.ps1` prunes the shared `PLAN.md`:

1. At each barrier, for every todo that passed: decide its ending per `close/ai-todos-format.md`'s
   "Two endings" first. For the Completed ones, call
   `~/.claude/skills/mega-todos/archive-batch.ps1 -Items "<id>|<what happened>", ...` once for the
   whole batch instead of hand-rolling the `complete-todo.ps1` loop and pathspec - it resolves each
   id against the live backlog only, never a `done/` glob (the exact shape that broke twice, see
   `done/855-mega-todos-step-e-archival-is-hand-rolled-every-barrier.md`), and returns `.Pathspec`
   naming both halves of every move plus `PLAN.md`, and `.Failures` for any id it could not resolve
   to exactly one file. A todo that advanced but left `## Acceptance` items unmet is not archived,
   however clean its builder's report read; a non-empty `.Failures` is not archived either until
   re-resolved (retry with the full filename stem as the id to disambiguate a live-backlog
   collision).
2. Commit the archival as one `CHORE: archive completed todos` commit per barrier, via `/commit`,
   passing the helper's `.Pathspec` as the commit pathspec - the main thread CAN invoke skills, so it
   uses the real one; the helper itself never commits.
3. Diff the set of ids actually archived or parked against the lane map from Step C, per
   `refs/delegation-doctrine.md`'s "Fan-out reconciliation" - an id in neither set is a silent drop,
   re-dispatch or park it, never assume done.

Then the wrap-up, per `/auto-do-todos` Step 9: `/code-check START_SHA..HEAD`, the full fast-check
floor, e2e if runnable. Park every unresolved DEV fork into its todo's `## Open questions` block per
`/auto-do-todos` Step 8. Also drain every builder's "Out-of-scope findings" section gathered during
Step D: file each as a properly allocated todo, `**Origin:** ai`, per `refs/delegation-doctrine.md`'s
"Out-of-scope findings" section - never the builder itself.

**Summary must report:** todos completed with shas, todos parked and why, every Step B exclusion with
its own reason (never a bare count), the lane map and actual achieved parallelism, every fork
auto-decided and what it picked, barrier failures and how they were repaired, final ctx% used, and
the verification result.
End with `<cc-autopilot:off>`.

## Notes

- Context thresholds do NOT apply the way they do in `/auto-do-todos`. The main thread holds lane
  assignments and barrier results only, so a run is bounded by the token budget and the lane map, not
  by a 40% context stop. Still check `node ~/.claude/skills/context-left/context-left.mjs` at each
  barrier; if it climbs past 50%, something is leaking full reports into the main thread - tighten the
  workflow's return shape rather than ending the run.
- Never invoke `/autopilot` or `/auto-do-todos` as literal slash commands. Their contracts are adopted
  by reference.
- Source of truth for the backlog: `.claude/todos/` per `~/.claude/skills/close/ai-todos-format.md`.
