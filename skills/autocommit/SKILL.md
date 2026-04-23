---
name: autocommit
description: Triggers on /autocommit and its subcommands (on, push, pushbump, pushnbump, off) to manage auto-commit mode.
argument-hint: "[on|off|push|pushbump|pushnbump]"
---

# /autocommit

> Toggle automatic committing after each completed task.

## `/autocommit` - Show State

Print current mode. Example: `autocommit: ON (commit + push)`

Possible states:

- `OFF`
- `ON (commit only)`
- `ON (commit + push)`
- `ON (commit + push + version bump)`

## `/autocommit on`

After each logical unit of work, automatically run `/commit`. Stay in this mode until `/autocommit off`.

## `/autocommit push`

After each logical unit of work, automatically run `/commit push`. Stay in this mode until `/autocommit off`.

## `/autocommit pushbump` (alias: `pushnbump`)

After each logical unit of work, automatically run `/commit pushnbump`. Stay in this mode until `/autocommit off`.

`pushnbump` is accepted as an alias and behaves identically.

## `/autocommit off`

Disable all auto modes. Wait for manual commit requests.

## Rules

Follow the `/commit` skill for all commit rules, prefixes, and shell rules.
