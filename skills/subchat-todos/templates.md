# /subchat-todos templates

Copy these into `.for_bepy/subchat-<YYYY-MM-DD>/` at the start of a run. They are derived from
the 2026-11-07 run's files.

## triage.md

```md
# /subchat-todos <date> - triage and decisions (orchestrator scratch)

Read-only scout read every AUTO todo on <date> against the tree at <START_SHA>. Every sub gets this
file. Your lane's todos are in your brief; use this for their scout notes, the settled decisions,
and which files other lanes own.

## Settled decisions (Joe, or decided by the orchestrator) - do not revisit

- <id>: <the decision, one line>.

## Known baseline failures at <START_SHA> (not yours to fix unless your lane says so)

- <check>: <failure>. Compare failures by identity against this list.

## Per-todo scout notes

### <id> <title>
Files (verified / NEW): <paths>. Tests that read them: <paths>.
Spec pack: <one paragraph>.

## Questions

<Joe is away: never call ask_user_question. A fork with a defensible answer: decide it and record it
in the todo's `## Decided` block. A fork with none: write it to the todo's `## Open questions`
block (format in `skills/auto-do-todos/SKILL.md` Step 8), leave the todo open, move on.>
```

## queue.md

```md
# Sub queue (orchestrator state, <date>)

START_SHA: <sha>   EXPECTED_BRANCH: <branch>

Conductor caps a chat at 5 subs (queued included) and refuses `after=` for a sub that is not yet
registered, so a follower is spawned when its predecessor reports back, from the brief below.

## Lanes

- <lane>: <sub-1> (<ids>) -> <sub-2> (<ids>) -> <sub-3> (<ids>)

## Follower briefs (spawn verbatim)

### <sub-2>
task: <under 80 chars>
goal: <what the lane is for>
done_when: <ids archived, tests named below green>
writes: true   files: [<paths>]   report_back: true
decisions: <settled decisions that apply>
prompt: <see the sub brief below>

## Log

- <sub> finished: <ids> archived (<shas>). Master tests: <result>. Left for Joe: <items>.
```

## Sub brief (the `prompt` field)

```text
You are one lane of a /subchat-todos run. Repo: <repo>. Read
.for_bepy/subchat-<date>/triage.md first: it has the settled decisions, the baseline failures and
which files other lanes own.

Your todos, in this order: <ids and titles>. Your files: <owned paths>. Everything else belongs to
another lane.

For each todo: claim it (`~/.claude/tools/claim-todo.ps1 -Id <id>`), build it, run the checks its
files need, commit via /commit, then close it with
`~/.claude/tools/complete-todo.ps1 -Id <id> -Note "<what happened>"`. A todo that advanced but did
not finish is not archived: leave it open with the reason in its Notes.

Joe is away. Never call ask_user_question. Decide a fork that has a defensible answer and record it
in the todo's `## Decided` block; park one with none in `## Open questions` and move on. A denied
tool call is a stop, not an obstacle to route around: park that todo.

A bug you find outside your files becomes a new todo (`**Origin:** ai`), not an edit.

Finish with one line: ids archived with shas, ids parked and why, the checks you ran.
```
