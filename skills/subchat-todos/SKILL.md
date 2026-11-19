---
name: subchat-todos
description: Triggers on /subchat-todos only. Runs the todo backlog through Conductor worktree subs, then reviews and gates the push.
disable-model-invocation: true
argument-hint: "[--plan-only] [todo ids]"
---

# /subchat-todos

> The backlog runs through Conductor subchats: one question round, a scout that splits the work
> into file-disjoint lanes, worktree subs that each close a few todos, a test run on master after
> every merge, then an independent per-commit review. Replaces `/loop-todos` (removed 2026-11-19);
> the mechanics come from the 2026-11-07 run, which closed 57 of 69 todos in 19 subs with zero
> merge conflicts.

**Trigger:** `/subchat-todos` only. Never auto-invoke.

**Needs Subchats mode ON** for this chat (its system prompt says so). If `spawn_chat` is not in
that mode, stop and tell Joe; there is no in-chat fallback.

## Adopted, not restated

- `skills/auto-do-todos/SKILL.md` Step 4 (AUTO and DEV triage, lean AUTO), Step 8 (the `## Decided`
  and `## Open questions` shapes) and its Precedence, Hard Stop and 3-strike rules.
- `skills/mega-todos/SKILL.md` Step B (exclusions, each with its own reason) and Step C (the scout's
  path existence check, test-coverage grep and trust-boundary pass; the main thread re-checks the
  union of paths in one batch).
- `refs/ai-todos-format.md` for the backlog, claims and `complete-todo.ps1`.
- `refs/delegation-doctrine.md`: orchestrator hygiene, report quality tells, fan-out reconciliation
  (a set difference of ids, never a count).

## State lives on disk

The run's state is `.for_bepy/subchat-<YYYY-MM-DD>/` in the repo (gitignored scratch):
`triage.md`, `queue.md`, `review-findings.md`. Shapes are in `skills/subchat-todos/templates.md`.
A `/respawn` mid-run resumes from `queue.md`; the orchestrator holds nothing the files do not.

## Phase 0 - The one question round

1. Collect every unchecked item in `## Open questions` blocks and, if any `## Deferred questions`
   blocks exist (each has a `<!-- loop-skip: dev deferred <date> -->` comment above it), ask ONE
   coarse card first: answer the N deferred questions now, or leave them deferred.
2. Filter: a question with a defensible default is a decision, not a question (auto-do-todos
   Step 5's recommendation gate). Ask only taste with no default, a hard stop (credentials,
   destructive, physical action) or a large hard-to-reverse blast radius.
3. ONE `ask_user_question` call with every survivor, each with 2-4 options, a recommendation, and
   two standing options: "you decide - autopilot it" and "skip this todo". No answer after about 30
   minutes means the dev left: treat every question as autopiloted.
4. Write back per todo: answered or autopiloted becomes a dated bullet under `## Notes` and the
   checkbox goes; skipped renames the heading to `## Deferred questions` with the `loop-skip`
   comment. A todo resolved this round keeps neither heading.
5. Skip list = every todo matching `loop-skip`, plus Joe's named exclusions. It never reaches a lane.

## Phase 1 - Preflight

A worktree sub branches from HEAD, so it cannot see uncommitted or untracked files and cannot merge
back over a dirty one. Before any spawn:

1. `git status`. Commit every dirty tracked file and every untracked `.claude/todos/*.md` via
   `/commit`. A dirty file that is not this run's to commit: ask Joe in Phase 0's card, never
   sweep it in.
2. Record `START_SHA` and `EXPECTED_BRANCH` in `queue.md`.
3. `list_peers`: if another session is active, `post_message` the run's scope once.
4. Exclusions per mega-todos Step B, each with a reason.

## Phase 2 - Scout

ONE read-only sub (`writes: false`, Sonnet, high), `report_back: true`, over the full text of every
AUTO todo. It returns per todo: AUTO or DEV, the verified file set, the test files that read those
files, and a one-paragraph spec pack. It also returns the settled-decision lines it found in the
todos' Notes. The orchestrator writes that into `triage.md`; the scout cannot, being read-only.

## Phase 3 - Lanes and queue

Partition by the transitive closure of file overlap (mega-todos Step C): two todos sharing any file
share a lane and run in order. Cut each lane into subs of 3-5 todos, sized to fit about half a sub's
context window. A todo with an unverified path does not dispatch.

Write `queue.md` with every lane's chain and each follower's FULL brief, up front. Conductor caps a
chat at 5 subs counting queued ones and refuses `after=` for a sub not yet registered, so a follower
is spawned only when its predecessor reports back, from the stored brief, verbatim.

**`--plan-only` stops here:** print the preflight result, the lane map and the path of `queue.md`,
spawn nothing.

## Phase 4 - Run

1. Spawn up to 5 first subs: `writes: true`, `files` = the lane's owned paths, `report_back: true`,
   Sonnet at high. Brief shape in `templates.md`. Every brief names `triage.md`, the claim and
   archive commands, `/commit` for every commit, and "never call ask_user_question: park a fork in
   the todo's `## Open questions`".
2. On each report_back wake-up, in this order:
   - Confirm the merge landed (`git log`, not the sub's word) and that its ids are archived.
   - Run the merged lane's own tests on master. Red: spawn one fix sub with `continue_from` the old
     one, before the lane's next follower. A second red parks the lane's remaining todos. Never
     revert or reset master.
   - Remove the merged worktree: `git merge-base --is-ancestor sub/<id> <EXPECTED_BRANCH>`, then
     `~/.claude/tools/safe-remove-worktree.ps1 -WorktreePath <path> -RepoRoot <repo root>`.
   - Append one log line to `queue.md` (shas, archived ids, what is left for Joe).
   - Spawn the lane's next follower from `queue.md`.
   - Send a one-line status bubble; with report_back on, the send-message stop guard demands one
     after 3 quiet wake turns.
3. Never schedule a prompt to poll subs. The app wakes this chat when a sub stalls or dies.
4. Re-read `.claude/todos/.claims/` at each wake-up; drop a newly claimed todo from lanes not yet
   started.

## Phase 5 - Closing question round

When every lane is done, run Phase 0's steps 2-5 over the `## Open questions` blocks the subs wrote.
If an answer moved a todo into the AUTO queue, run Phases 2-4 once more over only those todos. After
that second pass, leave anything still open for the next run.

## Phase 6 - Independent review

A sub's own "reviewer: ran" is not enough: the 2026-11-07 run's separate pass found 26 real issues,
two of them false auto-approves in live guards.

1. Run `skills/review-unpushed/SKILL.md` over `START_SHA..HEAD` (its Steps 1-3) and write the
   findings to `review-findings.md` grouped into lanes by area.
2. Fix lanes: spawn subs per lane exactly as in Phase 4 (briefs name the finding numbers and
   `review-findings.md`), 5 concurrent at most, same wake-up routine. Residuals a fix lane cannot
   finish become `**Origin:** ai` todos.
3. `/test` on master. Red stops the run and goes in the report.

## Phase 7 - Report and push

Push only if the invocation asked for it, and then only through `/gate-chat`: `spawn_chat` with
`gate: true` and a prompt quoting Joe's push request word for word. Otherwise leave the commits
unpushed and say so.

Final report, one bubble: todos closed with count, lanes and subs used, what is parked and why,
every exclusion with its reason, every decision auto-made, review findings fixed and filed, the
`/test` result, and what only Joe can do. Then the save step in `~/.claude/refs/save-step.md`.

## Notes

- The orchestrator never edits files itself except `queue.md`, `triage.md`, `review-findings.md`
  and Phase 0's todo write-back.
- Never commits directly; `/commit` owns that, in the orchestrator and in every sub.
- Backlog source of truth: `.claude/todos/` per `refs/ai-todos-format.md`, of the session's repo.
