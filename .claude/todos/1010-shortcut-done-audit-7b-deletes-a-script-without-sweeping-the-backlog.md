<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: nothing in this backlog covers post-deletion reference sweeping. 1006 concerns pasting the builder preamble, not deletion fallout. PLAN.md mentions shortcut-done-audit only as a scheduling line. -->
# 1010 - shortcut-done-audit step 7b deletes a script without sweeping the backlog for references to it

**Type:** skill-improvement
**Origin:** ai
**Created:** 2026-09-25

## Goal

Make `/shortcut-done-audit`'s step 7b, which deletes a closed ticket's one-off e2e script, also
check whether any open todo points at that script, so the backlog never ends up referencing a file
that no longer exists.

## Context

Step 7b was added to `skills/shortcut-done-audit/SKILL.md` in `9b9e791` on 2026-09-24. It deletes a
script once Joe confirms its ticket into `Complete` or `Won't do`, and it correctly tells him
whether the file is recoverable. It does not look at the backlog at all.

The same day, in zng-app, 14 one-off scripts were deleted by hand under the policy step 7b
automates. **13 open todos turned out to reference those 14 files**, and the damage was not
uniform:

- Five named the deleted script in their **acceptance criteria** (37, 151, 157, 158, 160). Those
  todos stayed valid but became unverifiable as written.
- Three were rendered moot outright (67, 112, 159), their entire subject having been deleted.
- One (173) had been holding a decision open for Joe that the deletion silently settled, so a cold
  session would have hunted for an answer that no longer existed.
- The rest were dangling citations.

None of this was predicted. It was found afterwards, by a concurrent session that happened to
notice one case, and generalised only when someone grepped for the other 13. A script deleted
through step 7b, one ticket at a time, produces the same breakage one file at a time, where it is
far less likely anyone notices.

## Approach

1. In step 7b, before deleting, grep the repo's `.claude/todos/` for the script's basename,
   excluding `done/`.
2. If there are hits, list them in the same per-ticket ask that already gates the deletion, so Joe
   sees "deleting this also orphans todos 37, 151" before answering rather than after.
3. On confirm, append a dated note to each hit naming the deleted file and the exact
   `git show <commit>~1:<path>` recovery command. Deletion by the orchestrator only, since
   `hooks/agent-todo-write-guard.py` blocks any dispatched agent from writing under
   `.claude/todos/` (see todo 1011).
4. Consider whether the note should distinguish an acceptance-criteria hit from a passing mention;
   the former makes a todo unverifiable and is worth flagging louder.

The bulk-case recipe, worth reusing for the wording: re-derive the affected set with
`git show --name-only --diff-filter=D <commit>`, drop the paths that still exist on disk, then grep
the backlog for what is left.

## Acceptance

- Step 7b greps the backlog before its delete prompt, and the prompt names any todo that would be
  orphaned.
- Confirmed deletions leave a dated note with a working recovery command in each affected todo.
- Verified on a real case, not reasoned: pick a ticket with a script and a referencing todo, run
  the step, and confirm the note landed and the recovery command actually returns the file.
