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
- If the dispatch captures screenshots: the already-resolved
  `.for_bepy/screenshots/<ancestor-pid>-<ancestor-start-ticks>/` path, computed by the
  orchestrator. A subagent cannot derive the ancestor PID itself, so a bare path or a
  description of how to compute it silently degrades to root, which `/close` can never claim.
- The orphan-check final step from `~/.claude/refs/process-hygiene.md` if it runs Node commands.
- The line: "Your final message is your entire return value. ALL commands, including the verify
  floor (build/test/lint/typecheck), run synchronously in the same tool call: `run_in_background`
  is FORBIDDEN in builder subagents, a long build is waited out, not backgrounded. Ending the turn
  while anything is still running is a failed dispatch."
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

If this dispatch captures screenshots, save them under
`.for_bepy/screenshots/<ancestor-pid>-<ancestor-start-ticks>/` (the orchestrator resolves this
path, a subagent cannot derive its own ancestor PID) - never a bare or hand-picked subfolder name,
that's what leaves files `/close` can never prove ownership of and therefore never clean up.

<OFF_LIMITS>

<ORPHAN_CHECK>

Your final message is your entire return value. ALL commands, including the verify floor
(build/test/lint/typecheck), run synchronously in the same tool call: `run_in_background` is
FORBIDDEN in builder subagents, a long build is waited out, not backgrounded. Ending the turn while
anything is still running is a failed dispatch.
```

`<WORKING_DIR>`, `<STAGING_LINE>`, `<OFF_LIMITS>` and `<ORPHAN_CHECK>` are the only fields the
orchestrator fills in per dispatch; the `.for_bepy/screenshots/` path is resolved by the
orchestrator (see above), not left for the subagent to compute. `<STAGING_LINE>` is `Stage your
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
