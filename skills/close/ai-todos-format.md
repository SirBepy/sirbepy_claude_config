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
  dropped-findings.log         # findings /code-check dropped rather than filed (append-only)
```

`dropped-findings.log` is not a todo and is never parsed as one. `/code-check` Step 4a appends
one line to it when a mechanical finding has no verification that would catch a mistake, so the
call stays recoverable instead of disappearing. Nothing reads it automatically; it is forensic
record, not a queue. It follows the same tracking rule as the backlog around it.

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
- `.claude/todos/*-.reserved` - ALWAYS, even in opted-in projects. Reservation markers are
  transient runtime state (see "Picking the next id" above) and must never be committed; each
  one is deleted at the point its real todo file is written, so a committed one would be a bug
  either way.

Appending the missing line(s) is idempotent self-healing; do it silently at point of use.

## Backlog file: filename and id

Zero-padded numeric prefix + kebab-case slug: `03-tighten-onboarding-step-redirect.md`.
The prefix is the stable id; the dev references tasks by id ("do todo 03").

**Picking the next id: reserve it, don't just read it.** Reading the directory for max+1 and
then writing has a race window between two concurrent sessions - observed three times in a row
on 2026-08-14 in this exact backlog (see [[336-todo-id-allocation-races-between-concurrent-sessions]]).
The id is claimed the same way execution is claimed:

1. Run `~/.claude/skills/close/reserve-todo-id.ps1 -RepoRoot <repo root>`. It scans
   `.claude/todos/*.md`, `done/*.md`, and any live `*-.reserved` markers for the current max
   numeric prefix, then atomically claims `max+1` by renaming a private temp file onto
   `.claude/todos/<id>-.reserved` with no-overwrite semantics (fails if the destination
   exists, same primitive the Claims mutex below uses). On collision it retries with a fresh
   scan, up to 20 attempts, so two sessions filing at once get two different ids without
   either overwriting the other. It prints the reserved id.
2. Write `.claude/todos/<id>-<slug>.md` using that id.
3. Delete `.claude/todos/<id>-.reserved` immediately after the write succeeds. This is the
   only way a reservation is consumed - do not leave it lying around.

**Abandoned reservations:** if a session reserves an id and crashes before writing the real
file, the marker is safe to reuse. A reservation is stale once its mtime exceeds 4 hours (same
threshold as the Claims staleness rule below) - `reserve-todo-id.ps1` prunes stale markers on
every call before it scans for the max, so this self-heals without a separate cleanup skill.

Never reuse ids, even after deletion. If a duplicate slips through anyway (e.g. a writer that
bypassed the reserve step), rename the later file to the next free id and re-check. Never
overwrite, never renumber the other session's file.

**If a collision slips through anyway** (both helper scripts below support this): pass `-Slug
<slug>` or the full filename stem as `-Id` to `claim-todo.ps1` / `complete-todo.ps1`; an
ambiguous id with no disambiguator errors naming both candidate filenames rather than guessing.

**A backlog file with NO numeric prefix is malformed.** The prefix IS the id, so a prefix-less file
cannot be referenced by the dev, cannot appear in PLAN.md, and cannot be ordered by `/plan-todos`.
Rename it via `reserve-todo-id.ps1` to give it one. Both helper scripts still accept its bare stem
as `-Id` and emit a warning naming that fix, deliberately: refusing outright would leave the file
archivable only by hand, and hand-archiving bypasses the claims mutex, which is the exact race the
mutex exists to prevent (three such files hit this during the 2026-08-19 run). Settled 2026-08-25
per todo 393: the scripts tolerate it, the contract calls it malformed, and neither pretends the
file is well-formed.

**Content-duplicate guard.** Applies to every writer (`/create-todo`, `/handoff`, `/close` Phase 3,
`/code-check`, autopilot) AND to `/cleanup-todos` relocation - moving a todo into another repo's
backlog is still a write into that backlog and gets the same check against the DESTINATION, not
just the source. The race guard above only catches two sessions grabbing the same id, not a second
todo covering work already filed under a different slug. Before writing, grep the destination
backlog and `done/` for keywords tied to the new todo's subject (tool/component names, the specific
question, any ticket id) and read hits in full. A hit resolves to one of three outcomes, never a
blind write:

- Destination has a LIVE todo for it: fold in, do not create a second file.
- Destination `done/` shows it DONE: the incoming copy is stale; drop it instead of filing it.
- Destination `done/` shows it DECLINED: drop it, and carry the decline reason forward (into the
  report, or the superseding file's Notes) so the same subject does not get filed again.
- **Handoffs are exempt from fold-in** - see Handoff mode below. A handoff matching a live handoff
  is still written as a new file with a fresh id, referencing the prior handoff's id and stating
  which of its facts are now superseded; it never edits, replaces, or deletes the old one.

No `done/` hit does not mean no history: if the todo asks to enforce a rule, also check whether
that rule was retired outright with no todo ever filed for it - `git log --oneline -- <the rule's
file>` (e.g. `CLAUDE.md`) grepped for the todo's keywords surfaces a removal commit even without a
`done/` entry. A hit there is the same DECLINED outcome above. Unattended (`/sleep-when-done`,
autopilot): never block on this - log the supersession and continue. `/create-todo`'s own
Anti-patterns section carries the concrete recipe this mirrors.

Backstopped by `hooks/todo-duplicate-guard.py`, a `PreToolUse` hook on `Write` matching
`\.claude/todos/\d+-.*\.md$`: it greps the destination backlog and `done/` for salient tokens
from the new file's title and blocks advisory-style, listing the candidate hit(s), when the
overlap is real (3+ shared tokens, or 2+ covering most of a short title) - a shared word or two
never trips it. Resolve a genuine hit via the three outcomes above; a false positive on a
distinct todo that only shares vocabulary is unblocked by adding `<!-- duplicate-checked -->`
anywhere in the new content.

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
file with a fresh id and a new PLAN.md line; old handoffs stay as history. This is the fourth
outcome the Content-duplicate guard above names: a handoff matching a live handoff is exempt from
fold-in, not blocked by it. Reference the prior handoff's id in the new file, state which of its
facts are now superseded, and add `<!-- duplicate-checked -->` up front - the new file predictably
shares enough vocabulary with the one it supersedes to trip `hooks/todo-duplicate-guard.py`.

The superseded handoff's PLAN.md line stays, annotated `- superseded by <new id>`, never removed:
deleting it would destroy the only signal that an older handoff existed, while annotating it costs
nothing and stops a puller from actioning the stale entry blind. Same asymmetry the guard itself
argues from - a stale entry left visible is recoverable noise, a deleted one is not.

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
- **The id is written plain, never bold/underscored/backtick-wrapped** (`- [ ] 12`, not
  `- [ ] **12**`). This settles a conflict found 2026-08-19: practice had drifted to bold ids,
  and `complete-todo.ps1`'s prune step didn't recognize that style, so completed todos left
  stale bold lines behind while the script reported success. The prune regex now tolerates
  `**id**`/`__id__`/`` `id` `` on read (so old bold lines and hand-edits still get cleaned up),
  but every writer of a NEW line uses the plain form from here on.
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
(the filename race guard covers it), and neither does archiving one when nothing was executed to
reach that outcome: a dev-instructed archival ("archive 05 and 12") or a verdict-only close with no
code written has no execution window a concurrent session could collide with - move it straight to
`done/` via `complete-todo.ps1`, no claim needed. This is not a loophole for skipping real work: any
todo where code is written, a file is edited, or a command is run to decide the outcome still claims
first, no matter how it ends (settled 2026-09-01, todo 484, after `hubbub-game-split-opinions`
showed two of four unclaimed completions were exactly this case, not a violation).

**Claiming is a side effect of the call that starts the work, never a separate remembered step.**
Every executor below (`/pickup`, `/batch-todos`, `/auto-do-todos`) claims in the same tool call that
begins reading or acting on the todo(s) - chained (`claim-todo.ps1 -Id 07; Get-Content <path>`), not
a preceding standalone call the model has to recall on its own. **Handling N todos in one pass costs
one remembered claim call, the same as handling one:** claim every id in the batch up front, in a
single `claim-todo.ps1` invocation, before starting work on any of them - see the batch form below.
A claim that has to be remembered once per todo is exactly the case that gets skipped when several
todos move together; collapsing N calls into one removes that failure mode without adding a fifth
place that says "remember to claim".

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
`<id>-<slug>.claim` so the two files claim independently.

**Batch form:** `-Id` accepts a comma-separated list (`-Id 03,04,05`) and claims every one of them
in this single call. `-Slug` only disambiguates a single id, so embed a colliding id's slug inline
as its full stem within the list instead (`-Id 03,434-real-slug,05`). Each id in the batch is
attempted independently - one bad or already-claimed id does not stop the rest from being claimed.
Exit codes cover the whole batch: 0 when every id claimed clean (fresh or reclaimed-stale), 1
(informational, not an error) when one or more ids lost to a live non-stale claim - those ids are
skipped, the rest are still claimed - and 2 when at least one id hit a genuine error (bad id,
ambiguity, filesystem failure).

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

## Two endings, and the tell that picks between them

**Every executor obeys this**, not just `/pickup`: `/batch-todos`, `/autopilot`, `/auto-do-todos`,
`/mega-todos` and an ad-hoc "do todo 07" all end a todo through this contract. Decide against the
todo FILE, not against how the session felt.

- **Completed** - every `## Acceptance` item is satisfied AND the Goal does not name an epic or
  multi-ticket outcome. Run `complete-todo.ps1` (or the manual three-step fallback): the file moves
  to `done/`, its PLAN.md line is pruned, the claim is released.
- **Advanced but not finished** - the Goal names an epic/multi-ticket outcome, OR one or more
  `## Acceptance` items are still unmet and this session did not address them. Real work landing
  never by itself makes a todo Completed.

For **advanced but not finished**: do NOT move the file to `done/` and do NOT run
`complete-todo.ps1`. Update the todo with what changed, refresh its PLAN.md line under the CAS
discipline above, release the claim by deleting `.claims/<id>.claim`, and name the remaining work
in the summary. The todo stays planned for a future run. An unattended run follows the same rule:
never archive a todo with unmet Acceptance items just because execution reached the end.

**`complete-todo.ps1` deliberately has no flag for this path** (settled 2026-08-25, todo 395). Its
three jobs are archive, prune and release; the not-finished path wants only the third, and a flag
that skips two of three would blur what the script guarantees. Deleting your own claim by hand is
not a race - the mutex governs acquisition, not release.

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
