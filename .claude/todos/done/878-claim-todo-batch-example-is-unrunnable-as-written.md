<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- Grepped this backlog and done/ for "claim-todo", "-Id", "batch claim". 794 refactors these two
     scripts' id-resolution fallback and 484 added the batch form; neither touches the doc example. -->
# claim-todo.ps1's own batch example fails with a PowerShell binding error

**Type:** task
**Origin:** ai

## Goal

Make `skills/close/claim-todo.ps1`'s documented batch invocation actually run, so the first thing a
session copies out of its help text is not a broken command.

## Context

Reproduced 2026-09-02 while claiming 12 todos for a `/mega-todos` batch. The script's own
comment-based help gives this example:

```
~/.claude/skills/close/claim-todo.ps1 -Id 03,04,05
```

`-Id` is declared `[string]`, so PowerShell parses the unquoted comma list as an **array** and
binding fails before the script body runs at all:

```
claim-todo.ps1 : Cannot process argument transformation on parameter 'Id'. Cannot
convert value to type System.String.
```

The working form is `-Id "03,04,05"`. The `.EXAMPLE` block, the `.DESCRIPTION` prose
("`-Id` accepts a comma-separated list (\"03,04,05\")" - correctly quoted there) and the
`.PARAMETER Id` prose ("a comma-separated list of either for a batch claim (\"03,04,05\" or
\"03,434-real-slug,05\")" - also correctly quoted) all disagree with the `.EXAMPLE` line, which is
the one a reader copies.

**Why this matters more than a typo.** Todo 484's whole point was that a claim call which has to be
remembered once per todo gets skipped exactly when several todos move at once, and the batch form is
the fix for that. A batch form whose advertised syntax throws on first use pushes the caller straight
back to per-todo calls, which is the failure 484 closed.

## Approach

Two options, and they are not equivalent:

1. **Fix the example only.** Quote it: `-Id "03,04,05"`. One line, zero behaviour change. The
   prose already uses the quoted form, so this just makes the example agree with it.
2. **Accept both forms.** Type the parameter `[string[]]` and join internally, so an unquoted list
   binds as an array and a quoted string still splits on commas. Kinder to the caller, but it
   changes the parameter's type and every call site plus `complete-todo.ps1`'s matching parameter
   would need checking for consistency.

Check `skills/close/complete-todo.ps1` and any other script in that directory for the same
parameter shape before picking, so the two do not end up disagreeing.

## Acceptance

- The `.EXAMPLE` line, as copied verbatim, runs without a binding error.
- If option 2 is taken, both `-Id 03,04,05` and `-Id "03,04,05"` claim all three, proven by running
  them against a scratch repo under `C:/tmp`.
- Whatever ships, `claim-todo.ps1` and `complete-todo.ps1` agree on the parameter's type and on how
  their help text writes the batch form.

## Notes

- Worth roughly a 5. Trivial to fix, but it sits on the path of a rule that is called
  non-negotiable, and it is the kind of defect that only shows up to whoever tries the documented
  form first.
- **Sequencing:** todo 794 is refactoring the id-resolution fallback out of both of these scripts
  into a shared `_shared.ps1`. It does not touch the parameter declaration or the help text, so
  there is no conflict, but land 794 first to avoid two edits racing on the same two files.
- Completed in /mega-todos wave 1 as part of commit 5aa6c0b (todo 901): the .EXAMPLE block in claim-todo.ps1 now shows both the bare and quoted comma forms, and -Id is [string[]] so both are actually runnable as written.
