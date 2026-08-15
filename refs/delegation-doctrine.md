# Delegation Doctrine

The shared rules for running the main agent as an ORCHESTRATOR instead of a worker. Imported by
`/delegate` (dev is present, interactive) and `/autopilot` (dev is AFK). Both skills point here;
neither restates these rules, so they can never drift apart.

This file is the delegation MECHANICS only. The model-tier and cost rules live in the global
`CLAUDE.md` "Subagent-Driven vs Inline Execution" section and are not repeated here: follow them
as written (every dispatch passes `model: 'sonnet'`; escalate above sonnet only on the triggers
listed there; tune `effort` freely). Process/orphan rules live in `~/.claude/refs/process-hygiene.md`.

## The 90/10 rule

The main agent's context is a planning surface, not a workspace. Roughly everything goes out to
subagents; the main agent keeps a narrow surgical exception.

**Subagents do:**

- All building. Every feature-sized edit, every multi-file change, every self-contained
  implementation chunk.
- All broad reading. Wide greps, whole-file reads, directory sweeps, multi-query web research,
  anything where the raw bytes are discarded once the conclusion is known.

**The main agent keeps SURGICAL rights:**

- A targeted read of roughly a few dozen lines when the exact `file:line` is already known.
- A trivial one-line fix (typo, import, constant) where a subagent round-trip would cost more
  than doing it directly.

The test is cost, not size-in-isolation: dispatch when the round-trip is cheaper than the context
the work would dump into the main thread. The main agent NEVER does a feature-sized edit itself,
however tempting the shortcut looks.

## Dispatch discipline

**Scout before builder.** For anything non-obvious, dispatch a read-only scout first and have it
return a condensed SPEC PACK, not a narrative: exact contracts (signatures, types, payload
shapes), `file:line` pointers, and the specific gotchas a builder would otherwise trip on. The
spec pack is what the builder prompt embeds, so the builder never has to re-derive the map.

**Every builder prompt embeds, without exception:**

- Its verify floor: the project's fast checks (typecheck, unit, lint, build) with the instruction
  to run them and report the actual output, not a claim of success.
- The comment-noise prefilter as part of that verify floor: run the command from
  `~/.claude/skills/commit/comment-noise.md` scoped to its own diff (`git diff HEAD -- <files it
  changed>`), trim until it prints nothing, and paste the clean output in the report. Requires a
  bash-capable shell for `awk` - the Bash tool on Windows dispatches, not PowerShell.
- The em-dash prefilter, same verify floor, same shell requirement: run
  `~/.claude/skills/commit/em-dash.sh` scoped to its own diff, same invocation and exit-code
  convention as comment-noise.sh above. A flag means fix that added line now, never a louder
  restatement of the no-em-dash rule - the rule was already stated verbatim in every dispatch of
  the run that broke it three times regardless (todo 290).
- The secret-scan prefilter, same verify floor and shell requirement: run
  `~/.claude/skills/commit/secret-scan.sh` scoped to its own diff. Unlike the other two, a hit is
  never auto-fixed - the builder stops and reports it. A dispatch prompt itself must never carry a
  credential either; name the env var the builder should read instead.
- The out-of-scope-findings channel: a subagent NEVER writes into `.claude/todos/`, even a
  well-formed, confident finding. It reports an "Out-of-scope findings" section instead - what it
  found and why it sits outside this dispatch's lane - and the orchestrator files it as a proper
  todo after the fan-out returns (see "Out-of-scope findings" below).
- The staging line, conditional on whether the repo shares a git index with concurrent sessions:
  default `Stage your changes but do NOT commit. The main agent will run /commit after your
  report-back.`; for a shared-index repo (e.g. zng-app, zng-biller) substitute `Leave all changes
  unstaged. The main agent will run /commit by pathspec after your report-back.` Subagents cannot
  invoke skills, so they must never commit, except `/mega-todos` agents, which commit via a
  branch-guarded procedure - see `~/.claude/skills/mega-todos/SKILL.md`. Include this line even
  when the dispatch provably touches zero git-tracked files (e.g. a gitignored scratch dir): the
  line is static boilerplate, not a judgment call, and omitting it on a case-by-case read is
  itself the failure mode - no exception, ever.
- The load-bearing global rules it needs, restated: PowerShell on Windows, the working directory.
  Subagents do not inherit session context.
- Any load-bearing project memory already known to the orchestrator (a prior fix, workaround, or
  failure recorded for this repo), restated inline. A subagent re-solving a problem memory already
  answered is a wasted dispatch.
- If the dispatched work matches a skill's own description, that skill's file path(s) - `SKILL.md`
  plus any refs it points to - not just its rules pasted by hand. Subagents cannot invoke skills at
  all, only the orchestrator can, so a matching skill never fires on its own inside a dispatch; the
  file path is the only route the subagent has to that content, and hand-copied rules drift from
  the source over time. Skip this only when the prompt already inlines everything the skill would
  have supplied. (todo 338, 2026-08-14: five Flutter e2e dispatches hand-copied the same driving
  rules instead of pointing at `flutter-e2e`'s files, because the skill can't invoke itself inside
  a subagent.)
- If the dispatch captures screenshots: the already-resolved `.for_bepy/screenshots/<pid>-<start-ticks>/`
  path. Resolve it ONCE per session via `~/.claude/skills/close/rename-session.ps1 -GetId`
  (`.sh --get-id` on Unix) and reuse that id for every dispatch this session makes. Never derive
  it from a process-tree walk and never hand-pick a folder name: `/close` can only delete its own
  authoritative subfolder, so a wrong id is permanently un-cleanable and may collide with a live
  session's folder.
- The orphan-check final step from `~/.claude/refs/process-hygiene.md` if it runs Node commands.
- The line: "Your final message is your entire return value. ALL commands, including the verify
  floor (build/test/lint/typecheck), run synchronously in the same tool call: `run_in_background`
  is FORBIDDEN in builder subagents, a long build is waited out, not backgrounded. Ending the turn
  while anything is still running is a failed dispatch. Any command that may exceed 120 seconds
  MUST pass an explicit `timeout` (up to 600000ms): the tool's default is 120s and the harness
  auto-backgrounds past it, so omitting `timeout` backgrounds your build whether you intended it
  or not."
- The line: "Never run `git stash`, `git reset`, or `git checkout` on paths you don't own: other
  agents' uncommitted work shares this tree. To compare against clean state, use `git show
  HEAD:<file>`."
- Stage changed files by name, never `git add -A` (parallel agents cross-stage each other's work
  otherwise).

## Canonical builder preamble

The block below is the literal text every builder dispatch prompt pastes for the "embeds, without
exception" list above, so it stops getting hand-retyped (and drifting) per dispatch. Fill in the
four placeholders; everything else is copy-verbatim. The per-dispatch parts - task, scope, OFF
LIMITS file list, verify floor specifics - stay hand-written, since those are the parts that
actually need thought.

```
Windows. PowerShell for shell commands. Working directory: <WORKING_DIR>.

<STAGING_LINE>

Never run `git stash`, `git reset`, or `git checkout` on paths you don't own - other agents'
uncommitted work shares this tree. To compare against clean state, use `git show HEAD:<file>`.
Stage changed files by name, never `git add -A`.

Never edit files under `~/.claude/` (skills, hooks, settings, global CLAUDE.md) even if the task
description points at one - that requires the dev's explicit say-so in the CURRENT session, which
a subagent can't verify; if a task seems to require it, stop and report back instead.

If this dispatch captures screenshots, save them under `.for_bepy/screenshots/<pid>-<start-ticks>/`,
the id the orchestrator resolved once via `rename-session.ps1 -GetId` (never a bare or hand-picked
subfolder name, and never one you derive yourself) - that's what leaves files `/close` can never
prove ownership of and therefore never clean up.

<OFF_LIMITS>

<ORPHAN_CHECK>

Your final message is your entire return value. ALL commands, including the verify floor
(build/test/lint/typecheck), run synchronously in the same tool call: `run_in_background` is
FORBIDDEN in builder subagents, a long build is waited out, not backgrounded. Ending the turn while
anything is still running is a failed dispatch. Any command that may exceed 120 seconds MUST pass
an explicit `timeout` (up to 600000ms): the tool's default is 120s and the harness auto-backgrounds
past it, so omitting `timeout` backgrounds your build whether you intended it or not.
```

`<WORKING_DIR>`, `<STAGING_LINE>`, `<OFF_LIMITS>` and `<ORPHAN_CHECK>` are the only fields the
orchestrator fills in per dispatch; the `.for_bepy/screenshots/` id is resolved ONCE per session by
the orchestrator via `rename-session.ps1 -GetId` (see above) and reused for every dispatch - never
re-derived per dispatch, never from a process-tree walk, never hand-picked. `<STAGING_LINE>` is `Stage your
changes but do NOT commit. The main agent will run /commit after your report-back.` by default, or
`Leave all changes unstaged. The main agent will run /commit by pathspec after your report-back.`
for a repo that shares a git index with concurrent sessions (e.g. zng-app, zng-biller).
`<ORPHAN_CHECK>` is the mandatory final-step text from
`~/.claude/refs/process-hygiene.md`, included whenever the dispatch runs Node commands and deleted
outright when it does not - it is a placeholder rather than verbatim text precisely so a
Node-running dispatch cannot lose it by pasting the block unread.

**Recovery.** If a builder parks itself waiting on a backgrounded command anyway, send one direct
resume: "deliver the final report now, no waiting." Expect to repeat it once before it complies.

**Parallelism.** Independent chunks fan out concurrently; anything that touches the same files
runs sequentially, or each builder gets its own worktree. Never let two builders write the same
file in parallel.

**Reports come back as conclusions plus evidence.** A subagent returns what it concluded, what it
changed, and the commands it ran with their real output. It does not return file dumps, search
results, or transcripts. Specify the report shape in the dispatch prompt.

## Out-of-scope findings

Decision (todo 291, 2026-08-12): a subagent never writes into `.claude/todos/`, no matter how
well-formed the finding - only the orchestrator can allocate an id without racing a concurrent
session, and an out-of-band write cannot see the claim/id-allocation guard the backlog contract
defines. A builder that wrote `.claude/todos/263-...` mid-dispatch collided with an already-taken
id within the same run, proving the race is real, not hypothetical. A PreToolUse write-guard hook
was considered and rejected here: it enforces mechanically, but the report-back channel keeps the
same finding without needing a new harness capability.

Every dispatch instead asks for an "Out-of-scope findings" section in the report: what was found,
and why it sits outside this dispatch's lane. The orchestrator turns each one into a properly
allocated todo after the fan-out returns, per the reporting requirement named above.

## Fan-out reconciliation

Partitioning a batch into dispatches by hand drops items silently, and nothing in a fan-out
notices on its own - every dispatch can report success while the union they cover is short one
item (todo 292, 2026-08-12: a 42-item batch grouped into 10 dispatches missed id 75, caught only
by an after-the-fact count mismatch while writing the archive notes). This is a set difference,
never a count comparison - counts match by coincidence when one item is duplicated and another is
dropped.

**Before dispatch:** write the union of ids assigned across every group and diff it against the
source list. State the expected total in the dispatch plan, so post-run reconciliation has
something to check against instead of re-deriving it.

**After the fan-out returns:** diff the set of ids actually reported on against that same source
list. An id in neither the completed nor the failed set is a silent drop - it must be
re-dispatched or parked, never assumed done.

## Liveness and session budget

Two failure modes the harness's own signals cannot see: a dispatched subagent that silently died,
and a fan-out that outlives the session's own token budget. Both leave the orchestrator holding
subagents it can no longer see into - context% tracks the ORCHESTRATOR's own usage, not the
children's, so a healthy context reading proves nothing about either hazard.

**Liveness.** The harness's "you'll be notified when it completes" phrasing invites trusting the
notification channel unconditionally - that is the exact failure mode (2h15m silent stall, 2026-07-28).
Before ending any turn with subagents still outstanding and nothing new to report, check the task
output dir's `LastWriteTime` (the `output_file` path is in every Agent tool result) against dispatch
time - NOT file size, a 0-byte output file is not evidence of death, one legitimately succeeded that
way. No growth in roughly the last 10 minutes on a dispatch expected to take 1-3 minutes (a read-only
scout) means presumed dead. Any fan-out of 3+ agents, or one with a 5-minute-plus ETA, additionally
gets a background watchdog: `Bash` with `run_in_background: true` running `sleep N` then a directory
listing of the task output dir, so a forced check-in happens even if every notification is lost.
Clean it up via `TaskStop` if the agents return first.

**Session budget.** Context% is not a session-budget signal: subagent tokens barely touch the
orchestrator's context (the whole point of delegating) while spending the same API session quota. No
direct session-quota signal is queryable, so the rule is on fan-out WIDTH instead: prefer per-item
completion over per-agent batching whenever a broken intermediate tree is expensive (a
typecheck-gated codebase, always), so an interruption leaves either completed-and-verified work or
untouched work, never a half-applied refactor spread across several files (4 agents died mid-edit
simultaneously on a session-limit reset, 2026-08-07, zero reports, an 18-file half-applied dedupe).

**Recovery when a fan-out is interrupted with no report.** Reconstruct state from `git status` plus a
real lint/test run before doing anything else; label every reconstructed verdict INFERRED, never
reported; file the handoff first.

## Orchestrator hygiene

After each subagent returns, keep ONLY the durable outcome in main context: one line for what
shipped, plus any parked item or open question. Discard the full report and every file body it
surfaced. The main thread accumulates decisions, never material.

## Quality tells (when to distrust a report)

Silent misses never look like failures, so these are judgment triggers, not automated ones. A
report is suspect when it is:

- Suspiciously clean: a big diff with zero findings, or every check green on the first try in a
  place that has historically been messy.
- Contradicted by other evidence: another subagent, the git history, or something already known
  in the main thread.
- Vague where it should be concrete: claims a check passed without the output, or describes work
  in the abstract without `file:line`.

Response: a targeted re-check (cheap, scoped to the doubt) or, for a high-stakes diff, one solo
higher-tier verifier per the global CLAUDE.md escalation triggers. Never accept a suspect report
just because re-checking costs tokens.

## Visual work

A builder whose task was visual (UI, layout, styling, mockup match) is never accepted on a green
verify floor alone: typecheck, tests and build cannot detect "this looks wrong". Its report must
include a rendered artifact, or the orchestrator renders one before accepting. Facing "it doesn't
look right", reach for a render before reaching for an explanation. (Table Night redesign,
2026-08-03: an 11/11-typecheck, 105-test, 4/4-build report shipped a screen nothing like the
approved mockup - a stale Vite dependency shadow that no automated check could see.)
