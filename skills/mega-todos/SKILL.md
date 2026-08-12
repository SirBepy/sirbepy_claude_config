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
question round with its 8-question cap. Read that file and run those steps as written. Triage logic
lives in exactly one place so the two skills cannot drift.

Everything from Step 6 onward is replaced by this file.

## Also adopted

- `~/.claude/refs/delegation-doctrine.md` in full, with ONE deliberate override: the verbatim
  stage-don't-commit line is replaced by the injected commit block below. Every other clause holds -
  scout spec packs, orchestrator hygiene, report quality tells, the no-`run_in_background` rule.
- `/autopilot`'s behavior contract: bounded `/iterate-it`, nested-question suppression, the 3-strike
  runaway guard.
- `~/.claude/refs/process-hygiene.md` for anything spawning Node.

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
6. The workflow run (Step D) - lanes execute in parallel, barriers verify.
7. Archival and wrap-up (Step E).

## Step A - Preflight

Record `START_SHA` (`git rev-parse HEAD`) and `EXPECTED_BRANCH` (`git rev-parse --abbrev-ref HEAD`).
`EXPECTED_BRANCH` is substituted into every builder's branch guard, so a peer session moving HEAD
mid-run stops the agents instead of scattering commits onto someone else's branch (see
`~/.claude/todos/55-commit-must-recheck-branch-before-each-commit.md`; a long wide run is the worst
case for that hazard). Then verify, in the target repo, the four conditions the injected commit block
depends on. Each is a one-line check and each has a defined consequence:

| Check | If present | Consequence |
|---|---|---|
| `GIT_FLOW.md` at repo root **AND** HEAD is a protected-trunk name (`main`/`master`/`develop`) **AND** the repo has a remote | branch-protection fires | agents would each stall on `AskUserQuestion`. **Abort the run** and tell the dev to branch first. |
| `.claude/commit-style.md` | overrides prefixes/grouping | read it once and paste its rules INTO the injected block. |
| `.claude/skills/run-tests/SKILL.md` | `/commit` step 6 | 45 agents would each run the full suite. Strip step 6 from the injected block; the barrier runs it once instead. |
| `list_peers` shows another session | shared tree | post once from the main thread naming the whole run's scope, then let agents skip their own peer check. |

All three conditions must hold together, mirroring `/commit` step 1a's real gate rather than a loose
proxy for it. `GIT_FLOW.md` alone is harmless on a feature branch, and treating it as sufficient
bricks the skill in every repo that documents its git flow, which is most of them.

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
- **`live-verify` / `verify ... live` todos.** They need the running app and the dev's eyes. A green
  verify floor cannot see "this looks wrong" (delegation doctrine, Visual work). Park them.
- **Anything a Hard Stop covers:** credentials, destructive or irreversible ops, physical action.
- **Todos whose fix is a UI/visual judgment call** with no approved mockup to match.
- **Anything already claimed in `.claude/todos/.claims/`.** Another session is executing it right
  now. A run this long outlives a single snapshot, so re-read the claims directory at every barrier
  and drop newly-claimed todos from lanes that have not started yet - a claim appearing mid-run means
  a peer took it while we were building.

Report the exclusion counts in the Step E summary. Never drop silently.

## Step C - Lane assignment

This is the step that makes parallel commits safe, so it is not optional and not eyeballed.

Dispatch ONE read-only scout (`model: 'sonnet'`, `effort: 'high'`) with the full text of every AUTO
todo. It returns, per todo: the exact set of files the fix will touch (`file:line` where known), and
a one-paragraph spec pack a builder can act on without re-deriving the map.

The main thread then partitions into **lanes** by the transitive closure of file overlap:

- Two todos sharing ANY file are in the SAME lane and run **sequentially** within it.
- Lanes share no files, so they run **in parallel** with no possibility of one agent's pathspec
  commit capturing another's half-written file.
- A todo whose file set the scout could not pin down goes in its own lane, alone. Never guess.

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

`log()` the lane map at run start so the dev can see the shape.

## Step D - The workflow run

Author the script inline. Shape:

- `pipeline()` over LANES, never over todos. Each lane's stage runs its todos in sequence inside one
  agent call chain, so ordering within a lane is guaranteed.
- One builder agent per todo, `model: 'sonnet'`, `agentType` default. Tune `effort` down for
  mechanical splits, up for anything with judgment.
- A **barrier** every batch for the cheap ladder, and a second, rarer barrier for the full one.

**Verify ladder** (settled with the dev 2026-08-10; generalised 2026-08-12).

Defined by ROLE, not by command. Resolve each role to the project's real commands during Step A and
state them in the run's opening `log()`. A ladder whose roles cannot be filled at all is a **hard
stop** - a wide parallel run with no verify floor is 15 agents committing unchecked.

| Role | When | Scope |
|---|---|---|
| **Cheap per-todo** | by the agent itself, before it commits | only what that agent touched |
| **Per-batch barrier** | every batch | repo-wide, must stay fast enough to run often |
| **Full floor** | every 10-15 completed todos | everything, including tests and e2e |
| **Final barrier** | once, at run end | see the rule below |

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
skills. Paste this verbatim into every builder prompt. Substitute `<EXPECTED_BRANCH>` from Step A;
leave `<FILES>` as-is, the agent fills that with its own owned paths:

```
COMMITTING IS PART OF YOUR JOB. You cannot invoke /commit as a skill, so follow this procedure
exactly. Do not improvise around it and do not skip a step because the change looks small.

1. A global PreToolUse hook BLOCKS raw `git commit`. Immediately before EVERY commit, write a fresh
   marker IN ITS OWN TOOL CALL, never chained with the commit (`;`/`&&`) - the hook inspects the
   whole command string BEFORE any of it runs, so a chained marker is always rejected whole (the
   hook needs one written within the last 2 minutes, and consumes only the oldest, so concurrent
   agents do not steal each other's):
   Set-Content -Path "C:\Users\tecno\.claude\hooks\.commit-marker-$([guid]::NewGuid().ToString('N'))" -Value "x"

2. Run `git status` and `git diff` scoped to YOUR files only.

3. Run the comment-noise prefilter against exactly the paths you are about to commit, replacing
   <FILES>. If it prints anything, TRIM those blocks to the cap (2 lines typical, 4 hard per block)
   before committing. Do not ask, just trim.

   { git diff HEAD -- <FILES>; git status --porcelain -- <FILES> | awk '$1=="??"{print substr($0,4)}' | while IFS= read -r f; do git diff --no-index -- /dev/null "$f"; done; } | awk '
   /^\+\+\+ b\// { f=substr($0,7); run=0; next }
   /^\+/ && !/^\+\+\+/ {
     l=substr($0,2); add[f]++
     if (l ~ /^[[:space:]]*(\/\/|\/\*|\*|#[^[!]|#$|--|<!--)/) { c[f]++; run++; if (run>max[f]) max[f]=run } else run=0
     next
   }
   { run=0 }
   END { for (k in add) if (max[k]>=5 || (add[k]>=20 && c[k]*100/add[k]>=25)) printf "%s %d/%d (%d%%) longest %d\n", k, c[k], add[k], c[k]*100/add[k], max[k] }' | sort

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

Alongside it, every builder prompt still carries the doctrine's canonical preamble minus its
stage-don't-commit line: working dir, PowerShell, the
`<OFF_LIMITS>` file list (this is where the lane's non-owned files are named), `<ORPHAN_CHECK>` when
it runs Node, and the no-`run_in_background` clause.

**The `<OFF_LIMITS>` list is load-bearing here in a way it is not in a normal dispatch.** In a
stage-only dispatch a stray edit is caught at review; here it goes straight into history. Name the
lane's owned files explicitly and state that everything else in the repo is another agent's.

## Step E - Archival, verification, wrap-up

Archival is **main-thread only**, because `complete-todo.ps1` prunes the shared `PLAN.md`:

1. At each barrier, for every todo that passed: `~/.claude/skills/close/complete-todo.ps1 -Id <id>
   -Note "<what happened>"`. One call per todo, sequential.
2. Commit the archival as one `CHORE: archive completed todos` commit per barrier, via `/commit`
   (the main thread CAN invoke skills, so it uses the real one).

Then the wrap-up, per `/auto-do-todos` Step 9: `/code-check START_SHA..HEAD`, the full fast-check
floor, e2e if runnable. Park every unresolved DEV fork into its todo's `## Open questions` block per
`/auto-do-todos` Step 8.

**Summary must report:** todos completed with shas, todos parked and why, exclusion counts by
category from Step B, the lane map and actual achieved parallelism, every fork auto-decided and what
it picked, barrier failures and how they were repaired, final ctx% used, and the verification result.
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
