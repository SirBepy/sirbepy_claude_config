<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-01, complexity=HARD, worth=6, reconfirm-count=1, content-hash=b34bcdcd -->
<!-- duplicate-checked -->
# /commit's comment-cap gate rejects four times per session instead of preventing once

**Type:** skill-improvement
**Origin:** ai

## Goal

Stop the write-doc-comment -> gate-rejects -> trim -> retry loop from repeating several times in
a single session. The cap is enforced correctly; what is missing is anything that surfaces the
number at the moment the comment is being written.

## Context

Pomalo session, 2026-08-31. `skills/commit/prefilter-gate.sh` bounced `git commit` **four
separate times** for `comment-noise.sh`, each time on a doc comment the same session had just
written:

1. `lib/core/router/app_shell.dart` 6-line class doc + `lib/core/theme/pomalo_motion.dart` at
   38% comment ratio
2. `lib/features/backlog/backlog_task_grouping.dart` 7-line function doc
3. `lib/features/planning/planning_screen.dart` 5-line added block
4. `lib/core/data/task_repo.dart` 5-line doc + `lib/features/done/done_grouping.dart` 6-line doc

Every rejection was correct and every fix was a trim. The rule is in global `CLAUDE.md` ("2 lines
typical, 4 lines HARD CAP per block, and added comment lines stay under ~25% of a file's added
lines once it adds 20+"), so this is not a missing rule - it is a rule that only fires after the
code is written, at commit time, when re-reading and re-trimming costs a full extra round trip
per file.

The ratio half is the sneakier one: `pomalo_motion.dart` was a brand-new 21-line file whose
per-field doc comments were individually well under the block cap and still tripped the 25% gate.
Nothing warns about that while writing a small file.

## Approach

Options, roughly in increasing cost - pick one, do not stack them:

- **A `PostToolUse` hook on Write/Edit** for source files that runs `comment-noise.sh` against
  just that file and reports the count inline, the way the `impeccable` design hook already
  reports on UI writes. Turns a commit-time rejection into a write-time note. This is the closest
  match to how the same problem was already solved elsewhere in this tree.
- **Have `prefilter-gate.sh` print the offending block**, not just `file 13/110 (11%) longest 6`.
  Cheapest change; still after the fact, but removes the "which block?" re-read that currently
  follows every rejection.
- Leave as-is and accept the loop. Defensible - the gate does work - but four rounds in one
  session is the evidence against it.

Check whether `hooks/` already has a comment-noise hook before writing one; the impeccable design
hook fires on the same trigger surface and may be extendable rather than duplicated.

## Acceptance

- A session that writes an over-cap doc comment learns about it before `git commit`, or the
  rejection names the block so the fix needs no re-read.
- `python ci/run_all.py` stays green (it covers every `hooks/test_*.py` suite; a new hook needs
  its own).
- `comment-noise.md` stays the single place the cap numbers are defined - do not restate them in
  a hook.
