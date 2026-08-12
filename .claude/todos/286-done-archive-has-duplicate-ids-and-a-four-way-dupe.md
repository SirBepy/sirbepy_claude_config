<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# The done/ archive has colliding ids and one fix duplicated four ways

**Type:** skill-improvement
**Origin:** ai

## Goal

Clean up the id collisions and duplicate entries that became visible in
`.claude/todos/done/` once the backlog was put under git, and decide whether the id contract needs a
guard so it cannot recur.

## Context

Surfaced by the `/code-check` verification pass of the 2026-08-12 `/auto-do-todos` run. Commit
`901e53b` put the previously-untracked backlog into git for the first time (todo 283), and the
one-time backfill made the archive's contents inspectable as a set rather than one file at a time.

Concrete collisions found:

- Two different files claim id `263`: `done/263-commit-marker-must-be-its-own-tool-call.md` and
  `done/263-skill-for-driving-android-emulator-ui.md`.
- Two different files claim id `98`.
- Four separate todos (`98`, `263`, `265`, `279`) all describe the same "the commit marker must be
  its own tool call" fix. Three were archived as duplicates of `265` on 2026-08-12; the pattern is
  that the same observation kept getting re-filed by different sessions.
- One file has no id at all: `done/commit-marker-must-be-its-own-tool-call.md`.

None of this breaks anything today, since `done/` is inert. It matters because
`complete-todo.ps1 -Id <id>` and the dedupe passes both key on id, so a collision makes an id
ambiguous, and because the four-way duplicate shows the creation-time content check was not catching
a restatement of the same defect.

## Approach

Two separable pieces, and the second is the one that actually pays off:

1. Renumber or merge the colliding archive entries so each id appears once, and give the
   id-less file an id. Purely mechanical, low value on its own.
2. Work out why the same fix was filed four times. `done/24` already added a content-level backlog
   overlap check to `/create-todo`, and todo 96 extended that to the other writers on 2026-08-12
   (commit `e6f2199`), so check first whether those two together already close it. If they do, this
   todo is just the cleanup in item 1. If they do not, the gap is that none of the checks look in
   `done/`, so a defect that was already fixed and archived gets re-filed as new.

## Acceptance

- No id appears on two files anywhere under `.claude/todos/`, active or archived.
- A stated verdict on whether `done/` needs to be inside the duplicate check's search scope, with
  the evidence either way, recorded in `close/ai-todos-format.md` if the answer is yes.

## Notes

- Filed by the wrap-up verification of the 2026-08-12 `/auto-do-todos` run, not by the dev.
