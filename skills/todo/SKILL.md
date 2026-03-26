---
name: todo
description: Manage a per-repo TODO backlog using /todo commands. Trigger immediately whenever the user types /todo (any subcommand), says "add a todo", "mark this as done", "let's plan todo", "todo session", or wants to track a task in the current project. Manages TODOs.md in the repo root, enforces a mandatory planning gate before any work starts. Never skip this skill when /todo is typed — even casually.
---

# Todo Skill

Manages a persistent `TODOs.md` in the current repo root. Every TODO has a lifecycle and **cannot be worked on until it has a written plan.** That gate is the whole point.

---

## Commands

### `/todo <description>`
Add one or more TODOs. Each line is a separate TODO.

1. For each description: parse it, generate a ≤6-word title, assign next ID, decide status (`pending` or `needs-clarification`)
2. Echo back the list of todos about to be added, then ask: "Anything else to add?"
3. Wait for Joe to confirm or add more. If more come in, accumulate and ask again.
4. Once confirmed: surface all open questions one at a time (see Session Mode). Do NOT commit yet.
5. Once all questions are resolved (or there were none): ask Joe via **AskUserQuestion** with options "Yes, commit" / "Not yet" whether to commit.
6. Only commit after Joe confirms. Write all entries to TODOs.md, update `<!-- last-id: N -->` once, then git commit: `todo: add [T-00N] <title>` (single) or `todo: add [T-00N] through [T-00M]` (batch)

---

### `/todo plan <id>`
Write or propose a plan for a TODO.

1. Read the entry
2. If Questions are unanswered → write them (or update them) and set status `needs-clarification`, ask Joe to `/todo clarify` before proceeding
3. If no open questions → propose a concrete plan (steps, approach, files involved), write it to **Plan**, set status `planned`
4. Ask Joe via **AskUserQuestion** with options "Yes, commit" / "Not yet", then git commit: `todo: planned [T-00N] <title>`

---

### `/todo clarify <id> <answer>`
Answer an open question on a TODO.

1. Find the first unchecked `- [ ]` question, mark it `- [x]` and append `: "answer"`
2. If all questions are now answered AND Plan is non-empty → promote to `planned`
3. If all questions answered but no Plan yet → stay `needs-clarification`, prompt Joe to run `/todo plan <id>`
4. Ask Joe via **AskUserQuestion** with options "Yes, commit" / "Not yet", then git commit: `todo: clarified [T-00N] <title>`

---

### `/todo start <id>`
Begin work on a TODO in the current session.

1. **Gate check**: if status is not `planned` → REFUSE. Say: `"[T-00N] isn't planned yet. Run /todo plan [T-00N] first."`
2. Set status to `in-progress`
3. No commit — status-only change.

---

### `/todo done <id>`
Complete and remove a TODO.

1. Confirm the entry exists
2. Remove the entire entry block from TODOs.md
3. Stage TODOs.md alongside any work files — the removal is always part of the same commit as the work, never separate
4. Ask Joe via **AskUserQuestion** with options "Yes, commit" / "Not yet" whether to commit everything together (skip this step if `--commit` was passed)
5. IDs are never reused — the `last-id` counter keeps incrementing

**Implicit done:** When work is completed that resolves a TODO (even without an explicit `/todo done` command), always remove that TODO from TODOs.md and include it in the same commit as the work.

---

### `/todo do <id> [--commit]`
Execute a TODO end-to-end: plan it if needed, do the actual work, then mark it done.

**ID normalization:** Accept `T-001`, `001`, or `1` — all resolve to `T-001`. Strip `T-` if present, parse as integer, zero-pad to 3 digits, prepend `T-`.

1. Normalize the ID
2. Confirm the entry exists
3. If status is `pending` or `needs-clarification` → run the `/todo plan <id>` flow first. If questions exist, ask them. Resolve all before proceeding.
4. Set status to `in-progress`
5. Implement the work described in the Plan. Follow each step in the Plan section.
6. Once work is complete, remove the entry block from TODOs.md (stage it alongside work files)
7. **Before committing:** follow all git skill rules - run the linter if one exists, fix every issue, then stage by file name
8. If `--commit` was passed: auto-commit using the git skill style, message: work-appropriate prefix + description. If not passed: ask Joe via **AskUserQuestion** "Yes, commit" / "Not yet"

---

### `/todo doall [--commit]`
Execute all todos end-to-end in sequence.

1. Collect all todos sorted by ID
2. If none → reply "No todos to do." and stop
3. For each TODO in order:
   a. Print: `Working on [T-00N] <title>...`
   b. Run the full `/todo do <id>` flow (plan if needed, implement, mark done)
   c. If `--commit` was passed, auto-commit after each TODO completes
   d. If not passed, ask once at the very end: **AskUserQuestion** "Yes, commit all" / "Not yet"
4. If any TODO fails or is blocked (unanswerable questions, unclear plan), stop and report: `"Blocked on [T-00N] — <reason>. Fix this first then rerun /todo doall."`

---

### `/todo planall`
Plan all unplanned TODOs via a one-question-at-a-time interview.

1. Collect every TODO with status `pending` or `needs-clarification`
2. If none → reply "Everything is already planned." and stop
3. Build a flat queue of all open questions across all todos, ordered by TODO
4. Ask them **one at a time**. For each question, offer 2-4 plausible answer options plus a "write my own" escape:

```
[T-001] Auth flow — 1 of 3 questions

What provider are you using?
  1. Supabase
  2. Firebase
  3. Custom / roll my own
  4. Something else (tell me)
```

5. Wait for Joe to pick a number or type a free-form answer. Apply it immediately to that question (`[x]`, append answer).
6. Move to the next question in the queue. Repeat.
7. Once all questions are exhausted — or Joe says "skip" / "done" — stop asking.
8. For every TODO where all questions are now answered, write the plan and promote to `planned`.
9. For TODOs with no questions at all, write the plan and promote to `planned`.
10. Ask Joe via **AskUserQuestion** with options "Yes, commit" / "Not yet", then git commit once: `todo: planall - planned N todos`
11. Report what got planned and what's still blocked.

---

### `/todo list`
Print a clean summary of all current TODOs grouped by status. No file changes.

---

## TODOs.md Format

```markdown
# TODOs

<!-- last-id: 3 -->

## [T-001] Short title here
**Status:** pending
**Added:** YYYY-MM-DD
**Description:** Full description of what needs to be done.
**Questions:**
- [ ] Unanswered question from AI
- [x] Answered question: "Joe's answer here"

**Plan:**
_(empty)_

---

## [T-002] Another todo
**Status:** planned
**Added:** YYYY-MM-DD
**Description:** ...
**Questions:**
_(none)_

**Plan:**
1. Do X
2. Do Y
3. Test Z

---
```

When creating the file fresh, include the comment block and a blank line before the first entry.

---

## Status Lifecycle

```
pending → needs-clarification → planned → in-progress → (removed on done)
```

| Status | Meaning |
|---|---|
| `pending` | Added, no questions, no plan yet |
| `needs-clarification` | AI has open questions |
| `planned` | Plan written, ready to work |
| `in-progress` | Being tackled right now |

---

## Planning Gate (non-negotiable)

If Joe asks you to implement, build, or fix something and it corresponds to an existing TODO that isn't `planned` or `in-progress`:

> "Hold up — [T-00N] hasn't been planned yet. Run `/todo plan [T-00N]` and we'll do this properly."

Do not start the work. This is the whole point of the system.

---

## TODO Session Mode

When Joe says "todo session", "dump some todos", or adds 3+ todos in quick succession:

- Add each one immediately, don't interrupt between them
- Accumulate all open questions silently
- After all are added, surface everything at once:

```
Added T-001 through T-004. Before I can plan these, I need some clarity:

**[T-001] Auth flow**
- What provider? (Supabase, Firebase, custom?)

**[T-003] Dark mode**
- Should it persist across sessions or follow system preference?
```

---

## Git Commits

Commits only happen when a TODO is being defined or redefined — not on status-only changes. Always ask Joe before committing using **AskUserQuestion** with options "Yes, commit" / "Not yet" — never ask via plain text. Never auto-commit (unless `--commit` flag was passed). If there are open questions on any TODO, resolve them first before asking to commit.

**Before every commit (no exceptions):** Read the `git` skill (`~/.claude/skills/git/SKILL.md`) and follow ALL its rules: run the linter, fix every issue it reports, use the right prefix, no AI attribution. This applies to done/doall commits too - not just planning commits.

| Command | Commits? | Message |
|---|---|---|
| `/todo <description>` | Yes, after confirmation | `todo: add [T-00N] <title>` |
| `/todo plan <id>` | Yes, after confirmation | `todo: planned [T-00N] <title>` |
| `/todo clarify <id>` | Yes, after confirmation | `todo: clarified [T-00N] <title>` |
| `/todo planall` | Yes, after confirmation | `todo: planall - planned N todos` |
| `/todo start <id>` | No | status-only |
| `/todo done <id>` | Yes, after confirmation | work files + TODOs.md in one commit |
| `/todo do <id>` | Yes, after confirmation (or auto with `--commit`) | work-appropriate prefix + description |
| `/todo doall` | Yes, after all (or auto per-todo with `--commit`) | work-appropriate prefix per todo |

**`--commit` flag:** Appending `--commit` to any command that normally asks before committing will auto-commit without asking.

If not in a git repo (no `.git` folder), skip commits and staging silently, note it once.

---

## Edge Cases

- **Duplicate description**: If a new `/todo` looks nearly identical to an existing one, flag it before adding: "Looks similar to [T-00X] — is this the same thing or distinct?"
- **Missing ID in command**: If Joe types `/todo done` without an ID and there's only one `in-progress` TODO, assume that one. If ambiguous, ask.
- **Empty TODOs.md after last done**: Leave the file with just the header and `<!-- last-id: N -->`. Don't delete the file.
