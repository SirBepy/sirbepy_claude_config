---
name: autocommit
description: Enable, disable, or check auto-commit mode for the session. Triggers on /autocommit and all its subcommands.
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

After each logical unit of work, automatically run `/commitpush`. Stay in this mode until `/autocommit off`.

## `/autocommit pushbump`

After each logical unit of work, automatically run `/commitpush v`. Stay in this mode until `/autocommit off`.

## `/autocommit off`

Disable all auto modes. Wait for manual commit requests.

## Rules

Follow the `/commit` skill for all commit rules, prefixes, and shell rules.
