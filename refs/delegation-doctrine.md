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
- The verbatim line: `Stage your changes but do NOT commit. The main agent will run /commit after
  your report-back.` Subagents cannot invoke skills, so they must never commit.
- The load-bearing global rules it needs, restated: PowerShell on Windows, never chain commands
  with `&&` / `;` / `|`, the working directory. Subagents do not inherit session context.
- The orphan-check final step from `~/.claude/refs/process-hygiene.md` if it runs Node commands.
- The line: "Your final message is your entire return value. Do not end your turn while your own
  sub-tasks are still running - collect all results first, synchronously if needed."

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
