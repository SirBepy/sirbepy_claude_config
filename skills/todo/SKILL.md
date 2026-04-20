---
name: todo
description: Triggers on /todo only, managing a per-repo TODO backlog with a mandatory planning gate before any work starts.
---

# /todo
> Manage a persistent TODOs.md backlog per repo, with planning gate enforcement.

Manages `TODOs.md` in the current repo root. No TODO can be worked on until it has a written plan.

## Commands

### `/todo <description>`
Add one or more TODOs.

1. Parse each line as a separate TODO, generate a ≤6-word title, assign next ID, set status `pending`
2. Echo the list back and ask: "Anything else to add?" Accumulate until confirmed.
3. Surface all open questions one at a time (see Session Mode).
4. Write to TODOs.md, then ask via **AskUserQuestion** "All done! Should I commit?" with options "Commit work done" / "Commit work done + removing Todo Task together" / "Do not commit". Commit: `todo: add [T-00N] <title>`

### `/todo plan <id>`
Ask all clarifying questions, then write the plan.

1. Read the entry. Generate a list of open questions needed to write a good plan (approach, constraints, files involved, etc.).
2. If there are questions: ask them one at a time via **AskUserQuestion** with 2-4 options plus "Something else". Wait for each answer before moving to the next. Write each answered question to the **Questions** field as `- [x] question: "answer"`.
3. Once all questions are answered (or there were none): propose a concrete plan (steps, approach, files), write it to **Plan**, set status `planned`.
4. Ask via **AskUserQuestion** "All done! Should I commit?" with options "Commit work done" / "Commit work done + removing Todo Task together" / "Do not commit". Commit: `todo: planned [T-00N] <title>`

### `/todo do <id> [--commit]`
Execute a TODO end-to-end.

Accept `T-001`, `001`, or `1` - normalize to `T-001`.

1. If not `planned`: run `/todo plan <id>` flow first, resolve all questions.
2. Set `in-progress`, implement each Plan step.
3. Remove entry block, stage alongside work files.
4. Run linter if one exists, fix all issues, stage by file name.
5. If `--commit`: auto-commit with work-appropriate prefix. Else ask via **AskUserQuestion** "All done! Should I commit?" with options "Commit work done" / "Commit work done + removing Todo Task together" / "Do not commit".

### `/todo doall [--commit]`
Execute all TODOs in sequence.

For each (sorted by ID): run `/todo do <id>` flow. If blocked, stop and report: `"Blocked on [T-00N] - <reason>."` If `--commit`: auto-commit per TODO. Else ask once at end.

### `/todo planall`
Plan all unplanned TODOs via one-question-at-a-time interview.

1. Collect all `pending` or `needs-clarification` TODOs.
2. Build a flat queue of all open questions across all TODOs, ordered by TODO ID.
3. Ask each question with 2-4 options plus "Something else". Wait, apply answer, move to next.
4. Once all questions resolved: write plans, promote to `planned`.
5. Ask via **AskUserQuestion** "All done! Should I commit?" with options "Commit work done" / "Commit work done + removing Todo Task together" / "Do not commit". Commit: `todo: planall - planned N todos`

---

## TODOs.md Format

```markdown
# TODOs

<!-- last-id: 3 -->

## [T-001] Short title here
**Status:** pending
**Added:** YYYY-MM-DD
**Description:** Full description.
**Questions:**
- [ ] Unanswered question
- [x] Answered question: "answer"

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

When creating fresh: include the comment block and a blank line before the first entry. After the last TODO is removed: keep the header and `<!-- last-id: N -->`, don't delete the file. IDs are never reused.

---

## Status Lifecycle

`pending → planned → in-progress → (removed on done)`

| Status | Meaning |
|---|---|
| `pending` | Added, no plan yet |
| `planned` | Plan written, ready to work |
| `in-progress` | Being worked on now (set by `/todo do`) |

---

## Planning Gate

If the dev asks to implement something tied to a TODO that isn't `planned` or `in-progress`:

> "Hold up - [T-00N] hasn't been planned yet. Run `/todo plan [T-00N]` and we'll do this properly."

Do not start the work. This is the whole point of the system.

---

## Session Mode

When the dev adds 3+ todos or says "todo session":

- Add each immediately without interrupting.
- Accumulate all open questions silently.
- After all are added, surface everything at once in grouped form.

---

## Git Commits

Ask via **AskUserQuestion** "All done! Should I commit?" with options "Commit work done" / "Commit work done + removing Todo Task together" / "Do not commit" - never ask in plain text. Auto-commit only with `--commit` flag. Resolve all open questions before committing.

Before every commit: read `~/.claude/skills/commit/SKILL.md` and follow all its rules (linter, prefix, no AI attribution).

| Command | Commits? | Message |
|---|---|---|
| `/todo <description>` | Yes | `todo: add [T-00N] <title>` |
| `/todo plan` | Yes | `todo: planned [T-00N] <title>` |
| `/todo planall` | Yes | `todo: planall - planned N todos` |
| `/todo do` | Yes | work-appropriate prefix + description |
| `/todo doall` | Yes per-todo | work-appropriate prefix |

If not in a git repo, skip commits silently, note it once.

---

## Edge Cases

- **Duplicate description:** Flag before adding: "Looks similar to [T-00X] - is this the same thing or distinct?"
- **Missing ID:** If only one `in-progress` TODO exists, assume it. If ambiguous, ask.
