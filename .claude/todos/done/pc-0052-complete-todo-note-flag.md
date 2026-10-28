<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- relocated: filed 2026-08-01 under shop-scraper's .claude/todos/30-*, moved here 2026-08-08 by /auto-do-todos per CLAUDE.md's "global work belongs in ~/.claude/todos/" rule -->
<!-- cleanup: last-checked never, complexity=unknown (shallow pass), reconfirm-count=1, content-hash=- -->
# Give complete-todo.ps1 a -Note flag

**Type:** skill-improvement

## Goal

Fold the "append a Notes block, then archive" two-step into the one script that already owns todo
completion. It was performed by hand 11 times in a single session.

## Context

Found 2026-08-01 during `/close` retrospective of a long `/auto-do-todos` session in shop-scraper,
which completed or archived 11 todos (04, 06, 08, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21,
22, plus decisions on 01).

`~/.claude/skills/close/ai-todos-format.md` already names
`~/.claude/skills/close/complete-todo.ps1` as the "preferred mechanism for the completion
sequence", and it correctly handles the three steps that matter for correctness: move to `done/`,
release the claim, prune the PLAN.md line under CAS discipline.

But `/batch-todos` step 6.4 requires something the script does not do: "Append a Notes line to the
todo recording what happened (completed + commit sha), THEN run complete-todo.ps1". So every
completion is two operations, and the first one is a raw `Add-Content` with hand-built escaping.
In practice that meant 11 `Add-Content ... -Encoding utf8 -Value "\`n## Notes\`n\`n..."` calls,
each a chance to fumble a backtick-n or an encoding flag, all doing the same thing.

It is a real papercut rather than a correctness bug: nothing went wrong this session. But it is
the highest-frequency manual step in the whole todo workflow.

## Approach

1. Add an optional `-Note <string>` parameter to `~/.claude/skills/close/complete-todo.ps1`. When
   supplied, append a `## Notes` section (creating the heading only if the file has none, since
   several todos already carry one) before performing the existing move/release/prune sequence.
2. Write it with `-Encoding utf8` explicitly. PowerShell 5.1's `Add-Content` defaults to the
   system ANSI codepage, and these files contain em dashes and Croatian characters.
3. Keep it idempotent and keep the no-note path byte-identical to today's behaviour, so existing
   callers are unaffected.
4. Update `ai-todos-format.md` and `/batch-todos` step 6.4 to point at the flag instead of
   describing a manual append.

## Acceptance

- `complete-todo.ps1 -Id 07 -Note "..."` appends the note and archives in one call.
- A todo that already has a `## Notes` section gets its note appended under the existing heading,
  not a duplicate heading.
- Running it with no `-Note` behaves exactly as before.
- Non-ASCII characters in the note survive the round trip.

## Notes

- Superseded by todo 10, executed in the same /auto-do-todos run on 2026-08-08: complete-todo.ps1 now has the -Note param. 10's approach was also the correct one - 52 proposed Add-Content -Encoding utf8, which would have injected the UTF-8 BOM the global shell-write rule bans.
