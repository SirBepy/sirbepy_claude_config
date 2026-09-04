<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: 869 and 864 are both this repo's OWN guards false-positiving; this one is a harness-level guard outside the repo, and this repo's guard was probed clean on the same input. -->
# A harness path guard blocks a PowerShell call on prose in a quoted argument

**Type:** task
**Origin:** ai

## Goal

Establish what actually blocks a PowerShell call whose only offence is a slash-prefixed word inside a
quoted string argument, and record the workaround so a future session does not spend the same time
suspecting this repo's own guards.

## Context

Hit 2026-09-04 during the `/mega-todos` wave-1 barrier. A `complete-todo.ps1` invocation was rejected
with:

    Remove-Item on system path '/mega-todos' is blocked. This path is protected from removal.

The command contained no `Remove-Item` and no removal verb at all. `/mega-todos` appeared only inside
a quoted `-Note` string, as prose. The message wording does not match any hook in this repo:
`grep -rn "protected from removal" hooks/ tools/ ci/` returns nothing, so it comes from the harness,
not from here.

`hooks/destructive-command-guard.py` was probed directly with the exact failing command text as a
`PreToolUse` payload and exited **0**, so this repo's guard is not the source and this is not a
regression from that day's todo 869, 797 or 835 work. Rewording the note to drop the leading slash
(`mega-todos` instead of `/mega-todos`) made the identical call succeed.

Worth pinning down because the block is silent about its own origin, and the natural first suspicion
lands on this repo's guards, which is where the time went.

## Approach

1. Narrow the trigger with a few probe calls: is it the leading slash, the word `Remove-Item`
   appearing anywhere in the session, the `.ps1` being invoked, or a proximity rule between them?
   Vary one thing at a time.
2. Once the trigger is known, record it in `refs/incidents.md` or a short note in
   `skills/close/ai-todos-format.md` next to the `complete-todo.ps1` usage, since archival notes are
   exactly where long prose containing slash-prefixed skill names gets written.
3. If the trigger turns out to be broad, consider having `complete-todo.ps1` read its note from a
   file rather than an inline argument.

## Acceptance

- The trigger condition is stated concretely, with the probe commands that establish it.
- A future session writing an archival note containing a `/slash-command` name either does not hit
  this, or finds the documented workaround where it will look.

## Notes

- Filed by /mega-todos on 2026-09-04. Not a defect in this repo, but it cost real time here.
- Fixed in e8291f5: the harness path-guard false positive and its workaround are recorded in refs/incidents.md. The trigger reads as a semantic classifier rather than a fixed regex, and the entry says so instead of overclaiming.
