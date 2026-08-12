# .claude/todos/ - backlog, plan, and claims contract

Single source of truth for the per-project todo system. Every skill that reads or writes todos
(`/close`, `/create-todo`, `/code-check`, `/batch-todos`, `/plan-todos`, `/pickup`, autopilot,
ad-hoc "do todo 07" runs) follows this file instead of restating its rules.

## Layout

All per-project, at the project root:

```
.claude/todos/
  07-fix-auth-redirect.md      # backlog: one md file per task
  12-continue-plan-layer.md    # handoffs are normal todos too
  PLAN.md                      # ordered To-Do lane (optional per project)
  done/                        # completed todos (moved here, ids stay burned)
  .claims/                     # active-claim lock files (NEVER git-tracked)
```

`.claude/todos/` is ALWAYS resolved relative to the repo root, with no exceptions. That includes
the global config repo itself: a session working on `C:\Users\tecno\.claude` writes to
`C:\Users\tecno\.claude\.claude\todos\`, never to `C:\Users\tecno\.claude\todos\`. The Conductor
app reads the repo-relative path, so a backlog anywhere else is invisible in the UI. Merged
2026-08-11 after the two locations split; the top-level copy no longer exists.

Historical note: this folder replaced `.for_bepy/ai_todos/` (migrated 2026-07-15). If a stray
`.for_bepy/ai_todos/` still exists in some repo, treat it as unmigrated legacy: move its files
into `.claude/todos/` before working.

## Git policy

Default: NOT committed anywhere. Any skill that writes into `.claude/todos/` first ensures
`.git/info/exclude` (local-only ignore, never the shared `.gitignore`) contains:

- `.claude/todos/` - unless the dev opted this project into tracking. Opt-in signal: any file
  under `.claude/todos/` is already git-tracked (`git ls-files .claude/todos/` non-empty).
  In that case do NOT add this line.
- `.claude/todos/.claims/` - ALWAYS, even in opted-in projects. Claims are machine-local state;
  committing them ships session ids and PIDs into history.

Appending the missing line(s) is idempotent self-healing; do it silently at point of use.

## Backlog file: filename and id

Zero-padded numeric prefix + kebab-case slug: `03-tighten-onboarding-step-redirect.md`.
The prefix is the stable id; the dev references tasks by id ("do todo 03").

**Picking the next id:** scan `.claude/todos/` and `done/` for the max numeric prefix, add 1.
Never reuse ids, even after deletion. **Creation race guard:** immediately after writing,
re-scan for OTHER files sharing your numeric prefix (a concurrent session may have taken the
same id with a different slug, so a filename-exists check alone is not enough). If a collision
exists, rename YOUR file to the next free id and re-check. Never overwrite, never renumber the
other session's file.

**If a collision slips through anyway** (both helper scripts below support this): pass `-Slug
<slug>` or the full filename stem as `-Id` to `claim-todo.ps1` / `complete-todo.ps1`; an
ambiguous id with no disambiguator errors naming both candidate filenames rather than guessing.

**Content-duplicate guard.** Applies to every writer (`/create-todo`, `/handoff`, `/close` Phase 3,
`/code-check`, autopilot). The race guard above only catches two sessions grabbing the same id, not
a second todo covering work already filed under a different slug. Before writing, grep the
destination backlog and `done/` for keywords tied to the new todo's subject (tool/component names,
the specific question, any ticket id) and read hits in full. A genuine match: fold its findings in,
or write a superseding file that references the old id - never leave two todos silently
disagreeing. Unattended (`/sleep-when-done`, autopilot): never block on this - log the supersession
and continue. `/create-todo`'s own Anti-patterns section carries the concrete recipe this mirrors.

## Backlog file: content

```md
<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# <one-line task title>

**Type:** task | skill-improvement
**Origin:** ai | dev

## Goal

One or two sentences. The user-facing or code outcome we're after.

## Context

Background a future cold AI needs. Pointers to prior commits, related files with `path:line`.
Why this is being deferred (so the AI knows what's already been considered).

## Approach

Concrete proposed steps. If a code shape was discussed, sketch it. Mention alternatives that
were rejected and why, so the AI doesn't re-litigate.

## Acceptance

- How to know it worked.
- What must NOT regress (pointers to recent fixes, edge cases).

## Verify        (optional - mainly for handoff todos)

- [ ] git pull
- [ ] <real commands the resuming session runs FIRST, in order, max ~6>

## Notes         (optional - freeform carryover)

Anything that fits no other section: design tradeoffs taken, unresolved WARNs, messages to the
next session.
```

- `**Type:**` values: `task` (default; absence means task) - code/config/analysis Claude can
  execute later. `skill-improvement` - skill gaps, "did this differently than the skill said",
  "this keeps coming up, maybe a skill" observations; its Approach names the skill file involved.
- `**Origin:**` values: `ai` - Claude noticed this on its own (a `/close` sweep, `/code-check`, an
  autopilot observation, a "this keeps coming up" note); the dev never asked for it in these
  words. `dev` - the dev asked for it directly, or it captures a decision he made; includes
  handoff todos, since those record his own in-flight work. Absent field on an older todo means
  unknown, and unknown is treated exactly like `ai` - nothing silently escapes the `/cleanup-todos`
  gate. Whoever WRITES the todo sets `Origin`; it is never upgraded from `ai` to `dev` just because
  the dev later read it or approved executing it - approval to execute is not authorship.
- Skip a section only if it genuinely doesn't apply. Never just a title and a one-liner.
- The bar: a future cold AI session must execute from the file alone. Handoff todos ("continue
  this in another chat") should be VERY descriptive - what was tried, where it failed, what the
  dev wants to achieve, what the misunderstandings were. Length is fine when it helps the next AI.
- **Done tasks:** move the file to `done/` (create the folder if missing) and delete the task's
  PLAN.md line if present. All executors do this - never plain-delete a completed todo.

## Handoff mode - shared by `/create-todo`'s bare invocation and `/handoff`

Both entry points produce the exact same artifact; this is the one place that behavior is
defined, so neither drifts out of sync with the other.

Type is always `task`. Origin is always `dev` - a handoff records the dev's own in-flight work,
never Claude's independent observation. The todo IS the session handoff - be VERY descriptive;
length is fine when it helps the next AI. Run the Content-duplicate guard above first - a handoff
is exactly the case that produced the original incident (two todos already covered the same fix,
caught only by luck reading filenames). Fill every section from the session itself, no
clarifying questions:

- **Goal** - what the dev is ultimately trying to achieve (the original ask, not the last subtask).
- **Context** - what was tried and in what order, where it failed or stalled, what the
  misunderstandings were (places the dev corrected course, wrong assumptions made), and any
  decisions already settled so the next AI doesn't re-litigate them.
- **Approach** - the concrete next steps as best currently known.
- **Verify** - up to ~6 real commands the resuming session runs first (start with `git pull` if
  the repo has a remote; include the project's fast checks if relevant).
- **Notes** - open decisions the dev still owes answers on, plus anything that fits nowhere else.
  If the invoking command was given a short freeform note, it goes here - it never overrides the
  auto-derived Goal/Context.

Then, always: prepend `- [ ] <id> - <short label>` to PLAN.md (create it with a `# Plan` header
if missing) per this file's CAS edit discipline below. This is the one backlog-creation path that
auto-plans; deferral-mode todos are NOT auto-planned - ordering the backlog is `/plan-todos`'s
job. A handoff never edits, replaces, or deletes a prior handoff todo - each call writes a new
file with a fresh id and a new PLAN.md line; old handoffs stay as history.

Confirm by printing the filename, a one-line summary, and "pinned to top of PLAN.md". Do not
execute the todo - filing it is the whole job.

## PLAN.md - the ordered To-Do lane

Optional per project. Backlog = everything, unordered; PLAN.md = what to pull next, in order.
Pointers only - task content lives in the todo files, never copied here.

```md
# Plan

## <optional phase heading>

- [ ] 12 - continue plan-layer work
- [ ] 07 [P]
- [ ] 09 [P]
```

- A line is `- [ ] <id>` plus an optional ` - <short label>` (a human-skimming courtesy; the id
  is the only authoritative part - never trust a label over the todo file's title) and an
  optional `[P]` marker meaning "safe to run in parallel with adjacent [P] items" (used by
  orchestrators dispatching subagents; unmarked = sequential).
- `## Phase` headings group items; order within and across phases is top-to-bottom execution order.
- NO claim or done state lives here. Claims live in `.claims/`; done = the line gets deleted.
- **Vanished ids:** a line whose todo file no longer exists in the backlog is silently pruned by
  the next reader - never an error.
- **Edit discipline (CAS):** PLAN.md is hand-editable and multiple sessions may touch it. Re-read
  the file immediately before every write, apply your line-level change to that fresh content,
  and keep edits line-scoped (prepend/insert/delete one line). Never rewrite the whole file from
  a stale in-memory copy. Parse forgivingly (stray whitespace, hand-edits).
- New handoff todos are PREPENDED (top of the first phase / top of file) - newest next.

## Claims - the mutex every executor obeys

Before ANY execution of a todo (picker, /batch-todos, autopilot, ad-hoc "do todo 07"): claim it.
Reading/browsing todos needs no claim - only execution does. Creation needs no claim either
(the filename race guard covers it).

**Claim = one file per task:** `.claude/todos/.claims/<id>.claim`.

1. Ensure `.claims/` exists and the git-policy exclude lines are present (self-heal above).
2. Write your claim content to a private temp name: `.claims/<id>.tmp-<pid>`.
   Content (informational, not load-bearing): `session: <session-id or pid-fallback>`,
   `pid: <pid>`, `started: <ISO timestamp>`.
3. Atomically rename it to `.claims/<id>.claim` with no-overwrite semantics
   (PowerShell: `Move-Item` WITHOUT `-Force`; it fails if the destination exists).
   - Rename succeeded -> you own the claim.
   - Destination exists -> someone else owns it; check staleness (below) before giving up.
   - Windows caveat: sync/antivirus filter drivers can throw a transient error that is NOT a
     lost race. Retry once after ~2s before concluding anything.
4. Clean up your temp file if the rename lost.

Scripted mechanism for the whole sequence above: `~/.claude/skills/close/claim-todo.ps1 -Id <id>
[-Slug <slug>] [-RepoRoot <path>]`. Implements steps 1-4 verbatim, including the retry and the
staleness rule below. When the id matches more than one backlog file (a known collision case -
see below), pass `-Slug <slug>` or the full filename stem as `-Id`; the claim is then named
`<id>-<slug>.claim` so the two files claim independently. Exits 0 on a fresh or reclaimed-stale
claim, exits 1 (informational, not an error) when someone else already holds a non-stale claim.

**Heartbeat:** while working, touch the claim file's mtime (PowerShell:
`(Get-Item <file>).LastWriteTime = Get-Date`) at natural checkpoints - after finishing a step,
after each todo in a batch. Never parse timestamps from the content; mtime is the liveness signal
(filesystem clock, no skew).

**Stale claim = BOTH signals dead:** mtime older than 4 hours, AND the PID in the file is not
alive on this machine (`Get-Process -Id <pid>` fails). If the claim file is from another machine
(PID meaningless), mtime alone decides. A stale claim may be deleted and re-claimed. A claim
that is old but whose PID is alive is NOT stale - a long session is working; skip that todo.

**Release:** delete `.claims/<id>.claim` when the todo completes or you abandon it. Completing
also means: move the todo to `done/`, delete its PLAN.md line.

Preferred mechanism for the completion sequence (append a Notes bullet + move to `done/` +
release claim + prune PLAN.md line, all four): `~/.claude/skills/close/complete-todo.ps1 -Id <id>
[-Slug <slug>] [-RepoRoot <path>] [-Note "<text>"]`. It finds `.claude/todos/<id>-*.md` (errors on
>1 match unless `-Slug` or a full filename stem as `-Id` disambiguates it, naming both candidate
files so the caller can retry; 0 matches is an error unless already in `done/`, in which case it
reports and no-ops). When `-Note` is passed, it appends `- <text>` under the file's `## Notes`
heading (creating one after `## Acceptance`, before any `## Open questions` block, if none exists)
before moving it - BOM-less UTF8, so a session never hand-writes this append. It then moves the
file, deletes the matching claim (plain or slug-suffixed) if present, and prunes the PLAN.md line
under this file's CAS discipline (fresh read immediately before the write). Idempotent -
re-running against an already-completed id reports clearly and makes no further changes. The
manual three-step sequence above remains the documented fallback if the script is unavailable.

## What belongs in the backlog

Tasks Claude can execute in a future session (code, config, skill edits, analysis), including
skill-improvement candidates and session handoffs. The wrong bar: "Claude can't test it" - that's
Claude's limitation, not a reason to defer. If the dev needs to physically do something first,
surface it directly in the response instead of filing a todo.

## Triggering execution

Claude does NOT auto-act on this folder. The dev triggers via `/pickup`, `/batch-todos`,
"do the AI todos", or naming an id.

## Off-limits content

Never include git instructions in a todo (commit, push, amend, tag). Git decisions belong to the
dev and the `/commit` skill. A todo describes WHAT to build, not how to close the session.
