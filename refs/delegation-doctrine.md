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

### When the Agent tool is unavailable

A harness directive ("do not call the AgentTool unless the user requested it"), a missing tool, or a
direct instruction from the dev can all put dispatch out of reach. **Do the step INLINE and name the
substitution in the run's summary.** Never call the tool anyway, and never silently drop the step.

This is a defined path, not a deviation to apologise for. Observed 2026-08-22 in
`hubbub-game-split-opinions`: the session did two rounds inline under exactly this directive and
self-reported both times, which worked, but it was a judgement call made twice under ambiguity when
it should have been a rule.

Inline is not automatically worse. Most fan-outs here buy CONTEXT ECONOMY, not capability, so
losing them costs main-thread tokens rather than quality - in that same session the inline
verification was stronger than a summarising subagent's would have been. The exception is a
dispatch whose whole purpose is keeping large bytes out of the main context: there, inline is a real
trade, so bound it by scope and SKIP with a stated reason above that bound rather than reading
everything inline.

A skill adopting this file inherits this clause; it does not need its own copy.

## Dispatch discipline

**Builder scope caps effort, not a parameter.** The `Agent` tool exposes `description`, `isolation`,
`model`, `prompt`, `run_in_background`, and `subagent_type` - no `effort` field (checked against the
live tool schema, 2026-09-10). A builder inherits the orchestrator's own effort at dispatch time, and
CLAUDE.md's "tune `effort` freely" cannot be executed for a subagent call: there is no knob to turn.
The only lever that actually exists is dispatch SCOPE - keep a builder small enough that even
inherited max effort converges before the output cap, and split any dispatch that would create more
than roughly six files into smaller ones. Open every builder prompt with an instruction to start
writing files immediately (one file per `Write` call) and keep each response short, rather than
reasoning at length before the first tool call. The failure this guards against already happened
(todo 965, 2026-09-05, Head Soccer build session `706da5d5`): a task-1.1 dispatch burned its whole
output budget on thinking and produced zero tool calls (`output_tokens: 64000`,
`thinking_tokens: 64000`, `stop_reason: max_tokens`); the retry only succeeded once the task was
split into three smaller dispatches whose prompts opened with the write-first instruction above.
Treat that exact signature - a report (or a quiet dispatch) with `stop_reason: max_tokens` and no
file changes on disk - as a failed dispatch needing a scope split, never a same-scope retry.

**Scout before builder.** For anything non-obvious, dispatch a read-only scout first and have it
return a condensed SPEC PACK, not a narrative: exact contracts (signatures, types, payload
shapes), `file:line` pointers, and the specific gotchas a builder would otherwise trip on. The
spec pack is what the builder prompt embeds, so the builder never has to re-derive the map. When
the spec pack must outlive the session (a successor, a builder fan-out), the ORCHESTRATOR writes
it to a file under `docs/research/` itself from the scout's returned text - a scout carrying the
`READ-ONLY DISPATCH` marker cannot reliably write that file itself: one told to write
`.for_bepy/impeccable-sweep/REPORT.md` had the call refused outright with "Subagents should return
findings as text, not write report files", and a repo-wide grep of `hooks/*.py` found no hook that
emits that string, so it is a harness-level restriction tied to the subagent carrying that marker,
not something this repo can patch (2026-10-03, fibo session 88f76f6a). Sibling dispatches in the
same run that carried no `READ-ONLY DISPATCH` line wrote their own findings files without trouble,
so a scout that genuinely must persist its own output skips the read-only opt-out and pastes the
normal preamble (screenshot-id line included, even though it writes no screenshots) instead - see
`refs/builder-preamble.md`'s read-only opt-out section. A report living only in context is gone at
the next respawn boundary, so anything a successor needs has to already be on disk before then
(2026-09-05, head_soccer_v_fable_oneshot). Use `subagent_type: general-purpose` for that
dispatch, never `Explore`: `Explore` strips the `Write` tool entirely, so a scout told to write a
spec pack under that type either fails the write or silently falls back to returning it inline,
forcing the orchestrator to copy 12-14 KB out of the report by hand (todo 994, Head Soccer session
51bc2e71). A `general-purpose` scout stays read-only in effect via its OFF LIMITS file list, not
via a stripped toolset; when the pack can stay inline in the report instead, skip the output file
and keep `Explore`.

**Claim before dispatch.** When a dispatch's work comes from a todo file, the orchestrator claims
that todo via `claim-todo.ps1` BEFORE dispatching the builder, and releases it via
`complete-todo.ps1` once the builder's report lands and the work is committed - or releases without
completing on an abort. This is the root `CLAUDE.md` claim rule ("before EXECUTING any todo, claim
it ... every path, including ad-hoc 'do todo 07'") applied to the dispatch path specifically: the
claim is the orchestrator's own action, never the builder's, since a subagent cannot reliably reach
`.claude/todos/` at all (`hooks/agent-todo-write-guard.py` blocks it) and the claim has to outlive
the builder's own lifetime regardless. `/autopilot` inherits this from here rather than restating it
(todo 1042: two todos shipped via dispatched builders with no claim ever taken, caught only after
the fact by `complete-todo.ps1`'s own warning).

**Todo-to-dispatch fidelity.** When a dispatch is built from a todo file, enumerate that todo's
Approach and Acceptance items before writing the prompt, then confirm each one appears in the
dispatch prompt or is explicitly excluded in it with a stated reason. A paraphrase is fine; a
silent drop is not (todo 465: a five-item Approach became a four-item TASK list, and the dropped
item, an oracle constraint, was caught only because the builder happened to volunteer it in its
out-of-scope-findings note, not because anything checked for it). This is the same set-difference
failure as "Fan-out reconciliation" below, at the scale of one todo's own steps rather than a whole
batch's ids - see that section for how the two scales relate. No hook enforces this: a dispatch
prompt carries no machine-readable link back to the todo id it came from, so a string-match check
cannot express "covers every item in a file it cannot identify" (todo 811). The enumeration above
and the out-of-scope-findings channel below are the only guards.

**Every builder prompt embeds, without exception:**

- Its verify floor: the project's fast checks (typecheck, unit, lint, build) with the instruction
  to run them and report the actual output, not a claim of success.
- The commit prefilters as part of that verify floor, scoped to the builder's own diff, with the
  per-script treatment split: fix an em dash, rewrite a comment-tense hit, STOP on a secret.
  There is no comment line-count scan; the comment rule judges content, not length. Verbatim text and the exact `prefilter-gate.sh` invocation live in
  `refs/builder-preamble.md`'s static block, not restated here so the two never drift apart - that
  drift is what let a builder ship three em dashes past a green CI on 2026-08-25, because the
  requirement lived only in this prose while the block every dispatch actually pastes said nothing
  (todo 791). They need a bash-capable shell for `awk`: the Bash tool on Windows dispatches, not
  PowerShell. A flag is a fix, never a louder restatement of the rule - the no-em-dash rule was
  stated verbatim in every dispatch of the run that broke it three times regardless (todo 290). A
  dispatch prompt must never carry a credential either; name the env var the builder should read.
- The out-of-scope-findings channel: a subagent NEVER writes into `.claude/todos/`, even a
  well-formed, confident finding. It reports an "Out-of-scope findings" section instead - what it
  found and why it sits outside this dispatch's lane, AND, when the dispatch was built from a
  source todo, anything in that todo the dispatch prompt did not ask for. That second half is the
  highest-value part of this channel: it is what caught the dropped item on todo 465, and naming it
  explicitly makes the rescue deliberate instead of lucky (todo 811). The orchestrator files each
  one as a proper todo after the fan-out returns (see "Out-of-scope findings" below).
- The staging line, conditional on whether the repo shares a git index with concurrent sessions OR
  with another builder the orchestrator is running at the same time in this same tree: default
  `Stage your changes but do NOT commit. The main agent will run /commit after your report-back.`;
  for a shared-index repo (e.g. zng-app, zng-biller) or a parallel-builder dispatch, substitute
  `Leave all changes unstaged. The main agent will run /commit by pathspec after your report-back.`
  and have that builder name its changed files in its report - the orchestrator commits by that
  list, never by `git diff --cached`, which can't tell one parallel builder's staged files from
  another's (see "Parallelism" below, todo 1061). Subagents cannot
  invoke skills, so they must never commit, except `/mega-todos` agents, which commit via a
  branch-guarded procedure - see `~/.claude/skills/mega-todos/SKILL.md`. Include this line even
  when the dispatch provably touches zero git-tracked files (e.g. a gitignored scratch dir): the
  line is static boilerplate, not a judgment call, and omitting it on a case-by-case read is
  itself the failure mode - no exception, ever.
- When the task's verification needs a before/after comparison, the dispatch itself supplies the
  baseline value or states the ordering (measure first, then edit) - see the "Taking a baseline"
  clause in `refs/builder-preamble.md` for the builder-facing mechanics.
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
- The orphan-check final step from `~/.claude/refs/process-hygiene.md`, unconditionally. It used to
  be gated on "if it runs Node commands", which let a subagent's whole-drive `find` escape it twice
  (todo 357); `refs/builder-preamble.md` now carries it as static body text, not a placeholder.
- The ban on `run_in_background` in builders, the mandatory explicit `timeout` past 120s, and what
  to do if a command still outlives its own 600000ms cap (report the partial output and name the
  command still running, never a bare "still waiting", todo 335) - verbatim text lives in
  `refs/builder-preamble.md`'s static block, not restated here so the two never drift apart.
- The bans on `git stash`/`git reset`/`git checkout` on paths it doesn't own, `git add -A`, and
  glob-based cleanup that could reach `hooks/.commit-marker-*` or `hooks/.session-markers/` (todo
  341) - same static block, same reasoning.

## Canonical builder preamble

The literal paste block every builder dispatch prompt embeds for the "embeds, without exception"
list above now lives in its own file, `~/.claude/refs/builder-preamble.md`, so it is read and
copied directly rather than hand-retyped (and drifted) per dispatch. That file has the block plus
its placeholder table, including the conditional `~/.claude` edit ban (`<GLOBAL_EDIT_BAN>`) and the
conditional orphan-check line (`<ORPHAN_CHECK>`) - both are placeholders, not body text, precisely
so neither can be pasted unconditionally by a hurried reader. A `PreToolUse` hook
(`hooks/dispatch-preamble-guard.py`) blocks a dispatch missing any of three always-required
markers, named here so a reader who never opens the other file still knows what they are:
(1) `Stage your changes but do NOT commit` OR `Leave all changes unstaged`, (2) `run_in_background`
AND `FORBIDDEN` both present, (3) `.for_bepy/screenshots/` OR the literal line `READ-ONLY
DISPATCH`. See that file's docstring and `refs/builder-preamble.md`'s read-only opt-out for what it
does and does not check. The per-dispatch parts - task, scope, OFF LIMITS file list, verify floor specifics -
stay hand-written, since those are the parts that actually need thought.

**Recovery.** If a builder parks itself waiting on a backgrounded command anyway, send one direct
resume: "deliver the final report now, no waiting." If that single nudge doesn't produce a real
report, the orchestrator takes verification over itself right away (run the check in the main
thread) rather than sending a second nudge - a second nudge only ever worked by telling the agent
to stop running commands and report facts it already had, which is the orchestrator doing the work
by proxy anyway (todo 335).

**Parallelism.** Independent chunks fan out concurrently; anything that touches the same files
runs sequentially, or each builder gets its own worktree. Never let two builders write the same
file in parallel. Every builder running concurrently with another in the same tree uses the
`Leave all changes unstaged` staging line (not the default stage-only variant) and names its own
changed files in its report; the orchestrator commits each chunk by that reported file list, never
by `git diff --cached`, which cannot tell one builder's staged files from another's already sitting
in the same index (todo 1061: another builder's staged deletions rode into an unrelated commit this
way and left HEAD uncompilable until the second builder's own commit landed).

**A shared registry file belongs to exactly one builder.** Files every feature touches (a
providers/DI file, `main.dart`, a router, an index barrel, `settings.json`) go in exactly one
dispatch's owned list and in every sibling's OFF LIMITS list; a sibling that needs a line there
returns it in its report and the orchestrator applies it. Until every still-running sibling whose
lane could reach a file has reported, do not commit that file. `commit-pathspec.sh` cannot catch
this case: the siblings write under the orchestrator's own session marker, so its one-marker
"solo session" test passes and auto-derived own ranges come back `clean` while another writer is
still active in the file (todo 1119: a commit carried a running sibling's half-finished providers
and HEAD stopped compiling).

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

That rejection was tested, not just theorized, and it broke: on 2026-08-19, during a 33-agent
`/mega-todos` run, a builder wrote `.claude/todos/391-builders-have-no-sanctioned-way-to-get-a-
whole-tree-baseline.md` directly, bypassing the report-back channel even though its dispatch
carried the "never write into `.claude/todos/` - report findings" line verbatim. It got lucky on
the id: 391 was free, so no collision happened, unlike the original todo 291 incident where the
same bypass produced a `263-...` collision with an already-taken id in the same run. **A mechanical guard CAN catch this. Probed and settled 2026-09-10** (todo 404), correcting this
paragraph's previous claim that no payload field distinguishes a subagent. The PreToolUse payload
`hooks/_hooklib.py`'s `read_payload` returns carries `agent_id` and `agent_type` when, and only
when, the call comes from a dispatched agent:

- A dispatched builder's own denied Write carried `agent_id`/`agent_type`, and an agent IT
  dispatched carried a DIFFERENT `agent_id` with the same `session_id`, so the field discriminates
  at any nesting depth.
- The orchestrator's own denied Write, fired from the top-level session, carried neither key at
  all: just `session_id`, `transcript_path`, `cwd`, `prompt_id`, `permission_mode`, `effort`,
  `hook_event_name`, `tool_name`, `tool_use_id`.

Both halves were captured the same way, by temporarily instrumenting `hooks/todo-duplicate-guard.py`
behind a marker file and firing a Write whose id was guaranteed to collide, so nothing was ever
created and the hook was reverted after. Absent means orchestrator, present means subagent.

The guard now exists: `hooks/agent-todo-write-guard.py`, wired `PreToolUse` on `Write|Edit`, shipped
2026-09-11 (todo 404). It denies a dispatched agent's write to a backlog file directly under
`.claude/todos/` and points it at the report-back channel below; an orchestrator write is untouched,
and so is a subagent's own `.claims/` write, since the path match requires the file to sit directly
in `.claude/todos/` with no further segment. The report-back channel is still the sanctioned route,
not a fallback: the guard stops the bypass, it does not carry the finding anywhere.

**In-hook detection is the only mechanism, and that is settled by experiment, not preference**
(2026-09-11, todo 434, Claude Code 2.1.261). The obvious alternative is to hang a hook off a named
agent type via `agents/<name>.md` frontmatter. It does not work:

- A frontmatter `hooks:` block is **inert** for an `Agent`-tool dispatch. Probed in a scratch
  project with a harmless always-exit-0 marker hook: the agent type itself loaded and ran
  (`subagent_stats` confirmed it), yet the run produced zero `hook_started`/`hook_response` events
  and no marker. The positive control matters: the identical hook wired through that scratch
  project's own `settings.json` DID fire and DID write its marker, so the instrument was working
  and the silence is a real negative.
- A frontmatter `permissionMode:` is partially honoured, in the useless direction.
  `bypassPermissions` genuinely takes effect (a Write denied for a plain agent succeeded for one
  carrying that value, same outer mode, single variable changed). `plan` showed no observable
  effect at all. Every value that works only LOOSENS; nothing tightens.

So a named agent type cannot carry a restriction. A guard that should apply to dispatched work only
stays globally wired and early-returns on the payload, the way `agent-todo-write-guard.py` does.
Re-probe before trusting this if the CLI version has moved on; the finding is version-scoped.

Every dispatch instead asks for an "Out-of-scope findings" section in the report: what was found,
and why it sits outside this dispatch's lane. The orchestrator turns each one into a properly
allocated todo after the fan-out returns, per the reporting requirement named above.

File each dispatch's out-of-scope findings the moment that dispatch's report lands, before the next
round launches - not batched to run end. A finding held only in the orchestrator's own context does
not survive a session that ends abruptly or a run with no end (todo 863, 2026-08-27: fifteen
dispatches, none filed until `/close`, several agents having died unreported in between).

## Fan-out reconciliation

Partitioning a batch into dispatches by hand drops items silently, and nothing in a fan-out
notices on its own - every dispatch can report success while the union they cover is short one
item (todo 292, 2026-08-12: a 42-item batch grouped into 10 dispatches missed id 75, caught only
by an after-the-fact count mismatch while writing the archive notes). This is a set difference,
never a count comparison - counts match by coincidence when one item is duplicated and another is
dropped.

This applies at two scales, and both are the same failure shape. **Across dispatches:** a batch of
todo ids gets partitioned into groups, and a group can be dropped whole - the id-union diff below is
that check. **Within one dispatch:** a single source todo's own Approach and Acceptance items get
paraphrased into one builder's task list, and an individual item can be dropped the same way (todo
465, 811: see "Dispatch discipline" above for the per-item enumeration check that guards this
scale). Keeping both under one heading is deliberate - treating them as unrelated lets a reader
believe the id-level rule already covers the within-dispatch case, which is exactly the gap that let
465 through.

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

**Liveness.** The task output file's `LastWriteTime`/size is not a liveness signal, in either
direction - measured directly (zng-app session `7ed111fd`, 2026-08-18/19, todo 384): an agent that
was demonstrably alive (writing PNGs to disk, 70-second-old timestamps) had an output file 775
seconds stale, and all four agents that had actually died silently had a 0-byte output file, the
exact case the old rule said not to trust. Never read that file's mtime or size as evidence of
anything. Check the agent's real effects instead:

- `git status --short` / `git diff --stat` scoped to the paths the dispatch assigned it - growth
  there is real progress.
- The artifacts it was told to produce (screenshots in its session subfolder, etc.) - check file
  presence/count directly, not the harness's own bookkeeping file.
- Whether it is still running at all: `TaskStop` against a bogus task id fails with a message
  listing every currently-running background agent ("Running background agents: ..."). That list is
  authoritative - if the dispatch's id isn't in it, the agent has already exited (cleanly or
  silently) and its last known state is final, not "still working." This is the cheapest true
  liveness probe available and costs one throwaway tool call.

**No background watchdog.** The old rule (`run_in_background` sleep-then-list on any 3+ fan-out or
5-minute-plus ETA) fired zero times across 8 dispatches in the incident session that prompted this
todo - a rule that depends on being remembered mid-fan-out does not survive being remembered.
Deleted, not fixed. Replace it with the unconditional habit that actually caught all four silent
deaths that session: **verify the tree yourself after every dispatch returns, and again before
ending any turn that has dispatches still outstanding** - run the effects check above (git
status/diff-stat, artifact check, project's own fast checks) every time, not only on suspicion. This
needs no new machinery and is cheaper than standing up and tearing down a watchdog process.

**Session budget.** Context% is not a session-budget signal: subagent tokens barely touch the
orchestrator's context (the whole point of delegating) while spending the same API session quota. No
direct session-quota signal is queryable, so the rule is on fan-out WIDTH instead: prefer per-item
completion over per-agent batching whenever a broken intermediate tree is expensive (a
typecheck-gated codebase, always), so an interruption leaves either completed-and-verified work or
untouched work, never a half-applied refactor spread across several files (4 agents died mid-edit
simultaneously on a session-limit reset, 2026-08-07, zero reports, an 18-file half-applied dedupe).

**Recovery when a dispatch returns quiet or with no report.** This is not a rare-case branch
anymore - the liveness check above already puts the orchestrator here after every dispatch, so
"recovery" is just what that check IS. Reconstruct state from `git status` plus a real lint/test run
before doing anything else; label every reconstructed verdict INFERRED, never reported; file the
handoff first.

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
- Verified by a method that could not have failed: the check's own construction guarantees a pass
  regardless of whether the feature works (see "Interaction work" below for the concrete case).

Response: a targeted re-check (cheap, scoped to the doubt) or, for a high-stakes diff, one solo
higher-tier verifier per the global CLAUDE.md escalation triggers. Never accept a suspect report
just because re-checking costs tokens.

**A builder that parks ("standing by", "will report back") is the orchestrator's catch, not a
hook's**, and `refs/builder-preamble.md`'s ban on it is unenforced by design. A hook sees one tool
call's payload; the parked-turn failure lives in a subagent's FINAL message, which no `PreToolUse`
matcher reaches, and the parent's `Stop` hook fires long after the dispatch already returned its
parked text as a result. So the tell is read here: a report whose deliverable is a promise rather
than an artifact is a failed dispatch, and it gets re-dispatched, never accepted and waited on.

After any dispatch that reported a teeth-check (mutate production code, watch a test fail,
restore), grep the changed non-test files for `if (true)`, `if (false)`, an early `return`, or a
commented-out guard before accepting the report - the builder's own restore claim is not proof
(see `refs/builder-preamble.md`'s matching clause and the revaire-mobile REV-5312 incident, todo
411).

## Visual work

A builder whose task was visual (UI, layout, styling, mockup match) is never accepted on a green
verify floor alone: typecheck, tests and build cannot detect "this looks wrong". Its report must
include a rendered artifact, or the orchestrator renders one before accepting. Facing "it doesn't
look right", reach for a render before reaching for an explanation. (Table Night redesign,
2026-08-03: an 11/11-typecheck, 105-test, 4/4-build report shipped a screen nothing like the
approved mockup - a stale Vite dependency shadow that no automated check could see.)

## Interaction work

A builder whose task depends on real browser input plumbing (drag and drop, focus and blur
ordering, pointer capture, native scroll, IME, paste, keyboard activation of links) must verify
with real input APIs, not `dispatchEvent`: Playwright `page.mouse.*`, `page.keyboard.*`,
`locator.dragTo()`, a real `focus()` plus typing rather than setting `.value`. A synthetic event
lets the test author choose `target`, `isTrusted`, and the event sequence, which are precisely the
things the real browser decides and the bug usually lives in. This does not ban synthetic events
outright: they stay fine for unit-level logic and for driving app state in a controlled way; the
failure is using them as proof of an integration that depends on browser plumbing. (Honeymoon-tools
drag-to-reorder, 2026-08-16: synthetic `dragstart`/`dragover`/`drop` events all passed while the
feature was fully broken for a real user, because the code's `e.target.closest('.drag-handle')`
guard can never be true when the browser sets `e.target` to the drag source, not the child under
the pointer - a dispatched event let the test choose `target` and hid exactly that bug. Re-verifying
with real `mouse.move`/`mouse.down`/`mouse.move`/`mouse.up` found the cause in one pass.)
