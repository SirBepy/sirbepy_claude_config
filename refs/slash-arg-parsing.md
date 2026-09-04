# Slash-arg chaining convention

A `/`-prefixed token appearing anywhere in an invocation's args is a chained command to run, never
context describing how the invoking skill should behave.

- A token starting with `/` opens a new chained command.
- Tokens between `/foo` and the next `/bar` are `/foo`'s args.
- Empty remaining args just means the invoking command runs bare, with nothing chained after it.

If a given pair's chaining is still ambiguous after applying this rule, ask up front - per
CLAUDE.md's front-load-all-questions rule - rather than picking a reading silently.

Incident this exists for: 2026-08-29, `/cleanup-todos /mega-todos` was read as `/mega-todos` being
mere context for how to run `/cleanup-todos`, instead of two chained commands. Only the cleanup pass
ran, reported as complete; the real `/mega-todos` run (44 todos, 48 commits) only started a full
cycle later.

`skills/close/SKILL.md`'s "Arg parsing" section is the worked example applying this rule to a real
skill's own boolean flags and chain examples.
