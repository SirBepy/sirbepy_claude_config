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
Never reuse ids, even after deletion. **Creation race guard:** if the write fails because the
filename already exists (another session grabbed the id), re-scan and take the next number -
never overwrite.

## Backlog file: content

```md
<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# <one-line task title>

**Type:** task | skill-improvement

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
- Skip a section only if it genuinely doesn't apply. Never just a title and a one-liner.
- The bar: a future cold AI session must execute from the file alone. Handoff todos ("continue
  this in another chat") should be VERY descriptive - what was tried, where it failed, what the
  dev wants to achieve, what the misunderstandings were. Length is fine when it helps the next AI.
- **Done tasks:** move the file to `done/` (create the folder if missing) and delete the task's
  PLAN.md line if present. All executors do this - never plain-delete a completed todo.

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
