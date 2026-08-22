# Refactoring method

Read this before a task whose point is to change structure without changing behaviour: extracting
a duplicated helper, splitting an over-long file, centralising constants, collapsing two copies
onto one. That is the class-2 finding `/code-check` Step 4a routes; the classes are defined there,
not restated here.

Adapted 2026-08-22 from `citypaul/.dotfiles`' `refactoring` skill (todo 425, item 2). It is NOT
adopted as a skill: `CLAUDE.md:27` says subagents cannot invoke skills, and subagents are what
execute nearly every refactor here, so the method has to arrive in the dispatch or not at all.
What follows is only the part that survives without that repo's Vitest/Stryker/TDD apparatus.

## 1. Establish a recoverable baseline, and say what it is

Before changing anything, name the state you can get back to and the evidence that it is good:

- The command that currently passes, by name. In `~/.claude` that is `python ci/run_all.py`.
- If nothing exercises the code, say so plainly. That is a fact about the task, not a formality
  to skip, and it changes what you are allowed to do next.

Never create a commit to make a baseline recoverable unless the dev asked for one. `git show
HEAD:<file>` recovers a single file without touching the tree other agents are working in.

## 2. The exercise test decides whether you may proceed

Name the specific command that would FAIL if this refactor were wrong, and say why it reaches the
lines you are changing. A repo-wide suite passing is not evidence for a file that no test imports.

Measured 2026-08-22, and it is why this section exists: a dead-symbol scan flagged
`hooks/_hooklib.py`'s `strip_quotes` as unreferenced. Two guards import it under an alias.
Deleting it would have failed both closed and `ci/run_all.py` would still have printed 4/4 green,
because neither guard has a test suite. Confidence is not coverage.

**If you cannot name that command, do not refactor.** Report what you found and stop. An unverified
behaviour-preserving change is just a change.

## 3. Priority: most findings are not worth acting on

| Priority | Action | Looks like |
|----------|--------|-----------|
| Critical | Now | One rule implemented differently in two places, control flow hiding a risky path |
| High | This task | Magic numbers, a name that misleads, one function doing three jobs |
| Nice | Leave it | Minor naming, a single-use helper |
| Skip | Never | Code that is already clear |

Only Critical and High justify touching code you were not sent to change. Nice and Skip are how a
refactor turns into the drive-by `CLAUDE.md` bans.

## 4. DRY is about knowledge, not about characters

Two blocks that look alike are not automatically duplication.

- **Collapse them** when they encode the same rule and would have to change together.
- **Leave them apart** when they are different concepts that happen to resemble each other, or
  would evolve independently. Coupling those is worse than the repetition.

`done/250` is the good case: five guards carried one scaffold, and it became `_hooklib.py`. The same
todo also records `tokenize()` being deliberately NOT unified, because two hooks differed in real
ways. Both calls were right.

## 5. Keep the change behaviour-preserving, and prove it

Small steps. Re-run the named command after each. If the diff changes what the code DOES, it is no
longer a refactor: stop, and report that the task needs a behaviour decision the dispatch did not
give you.
