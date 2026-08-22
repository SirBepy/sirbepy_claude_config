<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# code-style loads on a remembered instruction, and the harness mechanism that would replace it cannot fire on file creation

**Type:** task
**Origin:** ai

## Goal

Decide whether a `PreToolUse` hook should inject the matching `code-style/<stack>.md` when Claude
WRITES or EDITS a file of that stack, closing the gap that `.claude/rules/` structurally cannot.

## Context

Filed out of todo 424 (2026-08-22), which verified the `.claude/rules/` mechanism and then declined
to use it. Read `done/424-path-scoped-rules-are-unused-so-everything-is-always-loaded.md` first: its
"What the mechanism actually does" section has the full verified behaviour and should not be
re-derived.

The short version. `.claude/rules/*.md` with a `paths:` glob is real and works, but **its only
trigger is the `Read` tool.** Write and Edit never load a scoped rule. Because `Edit` requires a
prior `Read`, editing an existing file of a stack does load it; **creating a new file does not.**

That matters here specifically because the rule in question is:

> On first encounter with a project's stack, check `~/.claude/code-style/` for a matching file and
> follow its preferences. Read once per session.

"First encounter with a stack" is frequently a from-scratch file. So the harness mechanism misses
exactly the case the rule names, which is why 424 did not migrate it.

Meanwhile the current mechanism is a remembered instruction, and **todo 467 proved that class gets
silently skipped** - a long session read none of the four mandated once-per-session files, and one
of those skips led to six unasked-for pushes.

So `code-style/` is currently covered by a mechanism proven unreliable, and the obvious replacement
cannot cover its main case. A `PreToolUse` hook on `Write`/`Edit` matching by file extension is the
one option that fires on creation.

This was surfaced as a pivot by two independent raters on the 424 panel, both scoring the migration
low partly because this option was not on the table.

## Approach

1. **Measure before wiring, per the hook doctrine.** The question is not "would a hook work" but
   "how often would it fire, and on what". Count real `Write`/`Edit` calls by extension against the
   stacks `code-style/` actually covers. Note that `code-style/` holds only two files today
   (`luau.md`, `tauri.md`), so the addressable surface is small and that is itself an argument
   about worth.
2. Weigh the injection mechanism. A `PreToolUse` hook can return context, but injecting a 9000-char
   style file on every matching write is heavy; consider injecting only on the FIRST matching write
   per session (marker-file shaped, same primitive `commit-guard.py` and the screenshot reminder
   already use).
3. Consider the cheaper option honestly: leave the `CLAUDE.md` bullet exactly as it is. It is one
   sentence, it costs ~44 tokens, and 424 measured that its content was never in the gated budget.
   "Unreliable but cheap" may beat "reliable but a new hook to maintain" for a two-file surface.
4. If it ships, it needs a `hooks/test_*.py` self-test so `ci/run_all.py` covers it. Note that
   nothing in CI can currently test the `.claude/rules/` mechanism itself, which was one of the
   confirmed flaws against migrating.

## Acceptance

- A real measurement of matching Write/Edit frequency exists before any hook is written.
- A decision is recorded either way. "Leave it as prose" is an acceptable and possibly correct
  outcome, given the two-file surface.
- If a hook ships, it fires on a genuine new-file creation in a covered stack, proven by an actual
  run rather than by reading the code, and it has a self-test in `ci/run_all.py`.

## Notes

Do not reopen the `.claude/rules/` migration as part of this. That was decided on measurement in
424 and the verified mechanism is written up there; this todo is about the creation-path gap only.

The honest counterweight: `code-style/` covers two stacks. A new hook, its self-test, and its
maintenance may simply cost more than the rule is worth. Say so if that is where the measurement
lands.
