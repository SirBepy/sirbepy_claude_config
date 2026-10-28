<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-19, complexity=EASY, worth=9, reconfirm-count=1, content-hash=aecb4b7a -->
# /commit step 8 cannot catch a peer's dirty hunks inside a file you name

**Type:** skill-improvement
**Origin:** ai

## Goal

Make `/commit`'s step 8 require a `git diff` of every pathspec entry, not just a file-list
cross-check, so another session's uncommitted work in a file you name can no longer land in your
commit.

## Context

Real incident, 2026-08-18, `claude_usage_in_taskbar`, three concurrent sessions on `master`.

Session 23e410f9 committed `de401d36` naming `src-tauri/src/daemon/hooks_server/mod.rs` because it
had added one line (`mod activity;`). Session 53b9740a had two unrelated uncommitted lines in that
same file (`mod spawn_chat;` and a `/chat/spawn` route). Both landed inside `de401d36` under the
wrong message. Confirmed after the fact with
`git show de401d36 -- src-tauri/src/daemon/hooks_server/mod.rs`. Unrecoverable by then - four
commits from two other sessions were already stacked on it.

**The gap is in the skill text, not in the operator.** Step 8 warns at length about the shared
INDEX and about unpushed-commit overlap, and its only working-tree safeguard is:

> "Accepted trade-off: there is no `git diff --staged` review before the commit, so check the file
> list against the `git status` / `git diff` output from steps 2-3 before running it."

A pathspec commit takes each named path's entire WORKING TREE. `git status` renders one `M` line
whether a file is dirty because of you, a peer, or both - the file list is the wrong granularity
for the question, so every documented check can pass while foreign code ships.

Positive control the same day: 53b9740a ran `git diff -- chat-event-handler.ts chat-transforms.ts`
before committing, saw a third session's `AUQ_SKIPPED_TEXT` hunks mixed with its own three-line
removal, and held the files instead of sweeping them. Same rule, both directions, hours apart.

Lineage: `done/218` ("pre-stage git status sanity check") produced the commit-by-pathspec rule,
which fixed the INDEX half. This is the working-tree half it left open - a follow-up to 218, not a
duplicate of it. Captured as a project memory
(`feedback_diff_each_pathspec_file_before_commit`), but a memory does not change the procedure
every session actually executes.

## Approach

In `~/.claude/skills/commit/SKILL.md`, step 8's precondition list, replace the "check the file
list" trade-off sentence with a hard precondition alongside the existing branch guard and
unpushed-overlap check:

- Run `git diff -- <every pathspec entry>` immediately before `git commit`. Every hunk must be one
  you can account for.
- An unrecognised hunk is a STOP: either drop that path from the pathspec, or announce on the repo
  channel that you are taking the file whole and name whose lines ride along. Never assume a dirty
  file in your pathspec is dirty only because of you.
- Cheapest complement, worth naming in step 2: run `git status --porcelain` BEFORE the first edit
  of a session and keep that baseline. A file that was already dirty on arrival, or that goes
  dirty mid-session without your touching it, is the exact signal this check exists to surface.

Scope it to repos with concurrent sessions if the extra diff read feels heavy for solo work - but
note `list_peers` (step 7a) already runs unconditionally, so the condition is available for free.

Consider the same addition in `/close`'s chained-commit path, which reaches step 8 through the
same skill and inherits the gap.

## Acceptance

- `/commit` step 8 names `git diff -- <paths>` as a required precondition with the other three.
- The stop-and-ask behaviour on an unrecognised hunk is written down, not implied.
- A dry read of the new step 8 by a cold session makes it obvious that the `git status` file list
  is insufficient on its own - that is the misconception that caused `de401d36`.

## Notes

- 4dcfbd9: /commit step 8 now requires git diff of every pathspec entry before committing; an unaccounted hunk is a STOP.
