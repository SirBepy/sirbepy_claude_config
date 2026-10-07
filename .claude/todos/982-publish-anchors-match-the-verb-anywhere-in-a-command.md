<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-08, complexity=HARD, worth=8, reconfirm-count=3, content-hash=073b9545 -->
<!-- duplicate-checked -->
<!-- checked against 971 (done/, fixed 2026-09-11) and 951. 971 was about the guard prescribing a
     dry-run flag to tools that lack one, which is now fixed per tool; this is a different failure,
     the anchor firing on text that is not a publish invocation at all. 951 is the settings.json
     Read/Bash deny globs, a different layer entirely (permission rules, not a hook's own regex),
     and it is deferred. -->
# The publish guard's anchors fire on any command that merely contains the verb

**Type:** task
**Origin:** ai

## Goal

Stop `hooks/destructive-command-guard.py` blocking commands that mention a publish verb without
invoking one, without weakening what it catches.

## Context

Found 2026-09-11, twice in one run, by two parties that had no contact with each other.

`PUBLISH_ANCHOR_RE` and the new per-tool tables from todo 971 match a publish verb by position in
the command string, with no check on whether the invocation is actually a publish.

**Data point 1, from the todo 971 builder.** `npm publish --help` is CORE-denied. The builder hit
this while researching which tools support a dry run, and had to work around it with
`npm publish --dry-run --help`. Asking a tool for its own help text is not a release.

**Data point 2, reproduced first-hand by the orchestrator.** A `python` heredoc whose SOURCE TEXT
listed publish commands as test-case strings was denied outright, with the guard naming a missing
`--dry-run`. Nothing was being published; the words sat inside a quoted list of probe inputs. The
workaround was to write the script to a file first and run the file.

The second case is the more serious shape: the guard reads the command STRING, so any command whose
arguments happen to contain the verb trips it. That covers a heredoc, a `grep` pattern, an `echo`, a
commit message, a test fixture. It also means a session cannot easily write ABOUT these commands.

This is the same failure class todo 951 records for the word `build` (a bare token resolved as if it
were a command), reached through a different mechanism: 951 is the settings permission layer, this is
one hook's own regex. Fixing either does not fix the other.

A guard that denies an obviously harmless command trains people to reach for the bypass, which is
worse than the guard not existing. The bypass here is a session-level env var, so it is all-or-
nothing: a user who sets it to get past `npm publish --help` has disarmed every destructive check for
the rest of the session.

## Approach

1. Reproduce both cases first. They are cheap: pipe a payload whose `tool_input.command` is
   `npm publish --help`, and another whose command is a heredoc containing the verb inside quotes.
   Do not build on this description alone.
2. Add a help-invocation exemption: an anchor match whose command also carries `--help`, `-h`, or
   `help` in the verb position is not a publish. This is the narrow, obviously-correct half.
3. The heredoc/quoted-text half is the real design question. Decide between: only matching the verb
   at the START of a command or immediately after a shell separator (`;`, `&&`, `||`, `|`), versus
   stripping heredoc bodies and quoted strings before matching. Prefer the first if it holds: it is
   a smaller change and does not require the guard to parse shell quoting, which it will get wrong.
   Whichever is chosen, say what it still misses.
4. **Prove the guard still catches every real publish it catches today.** The existing suite in
   `hooks/test_destructive_command_guard.py` is 148 cases and is the regression net; every one must
   still pass. Add the new negative cases beside them.
5. Check whether the same positional over-match affects the guard's OTHER anchors, not just publish.
   If it does, say so and scope the fix consistently rather than special-casing publish. Data point 3
   below already answers this: it does. Scope the fix to the matching layer, not to one anchor.

## Acceptance

- `npm publish --help` and the equivalent for every tool family in the table are allowed.
- A command whose only occurrence of a publish verb is inside quoted data or a heredoc body is
  allowed, or the limitation is documented with a stated reason if it cannot be done safely.
- Every one of the existing 148 cases still passes; no real publish invocation becomes allowed.
- The change is written in ONE complete file write, never partial edits: this is a live guard that
  every concurrent session runs on every Bash command.
- `python ci/run_all.py` passes.

## Notes

- Phase 0 answer (Joe): fix steps 3 and 5 in this loop, with tests covering both the false positives and the true positives the guard must keep catching. (2026-10-07, /loop-todos Phase 0)
- Do not widen the bypass env var as the fix. It disables every destructive check at once, which is
  the opposite of what a false positive should cost.
- `hooks/destructive-command-guard.py` is tiered (CORE denies, MIDDLE asks). A false positive in the
  CORE tier is strictly worse than in MIDDLE, so if only one tier can be fixed cheaply, fix CORE.

**Data point 3, same run, and it is NOT a publish anchor.** A PowerShell call combining a real
`Remove-Item` of a reservation marker with an unrelated `-Note "..."` argument was refused with
`Remove-Item on system path '/loop-todos' is blocked`. The guard had picked the token `/loop-todos`
out of the NOTE TEXT, several hundred characters away from the `Remove-Item`, and treated it as that
command's target path. The actual target was an ordinary file under `.claude/todos/`.

This settles Approach step 5 before anyone starts: the over-match lives in how the guard associates
tokens with a command, not in the publish table. Any fix scoped only to publish anchors leaves the
destructive-path anchors matching the same way. It also shows the failure is not limited to a verb
appearing in argument text; a bare slash-prefixed word anywhere in the command reads as a path.

### Approach step 2 DONE, steps 3 and 5 deliberately NOT, 2026-09-11

The help-invocation exemption shipped. The rest was withheld on purpose: steps 3 and 5 change how a
CORE safety guard associates tokens with a command, and the direction of that change is "fire less",
which is not a call an unattended run should make. Step 2 is different in kind, and that is why it
was taken: a command carrying a help flag does not execute the destructive action, so exempting it
cannot let a real destructive command through.

**Shipped.** `is_help_invocation()` in `hooks/destructive-command-guard.py`, applied per
`verb_segments()` segment inside `match_publish_no_dryrun` and `match_publish_no_preflight`. Handles
`--help`, `-h`, and the swapped `<tool> help <verb>` form. That last one needed no code: the anchors
are anchored at the verb position, so `npm help publish` never matched in the first place. It is now
covered by regression tests so a future anchor-table edit cannot silently break it.

**Scoped per segment, not per command string**, which is the trap this todo is itself about,
reproduced in the opposite direction. A help flag in one segment must not excuse an anchor hit in
another. Both compound cases are tested and both still block.

Suite went 148 to 174 cases. Verified independently by the orchestrator across 15 invocations: five
tools' help forms allowed, `-h` allowed, the swapped `help` form allowed, four bare destructive forms
still caught, both compound traps still caught, and a real preflight still allowed.

### What is left

- **Step 3, the real one.** A verb inside quoted text or a heredoc body still matches. Two of this
  todo's three data points are that shape, including the one where a `Remove-Item` call was refused
  because the token `/loop-todos` appeared in an unrelated argument several hundred characters away.
- **Step 5.** The exemption covers the publish anchors only. `match_rm_rf`, `match_remove_item`,
  `match_chmod_777`, `match_mkfs_dd`, `match_disk_wipe_win`, the SQL matchers and the git
  force-push/reset matchers live in sibling `_destructive_guard_{fs,sql,git}.py` modules that were
  outside the dispatch's lane. `match_diskpart` and `match_disk_doctor_delete` live in the main file
  but were left alone too: whether a help flag is meaningful for those tools was not verified.
- Data point 3 already settles the question step 5 poses: the over-match is in the matching layer,
  not in the publish table, so the eventual fix belongs there rather than repeated per anchor family.

