<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: todo 864 is the same substring-matching SHAPE but on hooks/dev-backend-guard.py's DEV_MARKERS; this is a different hook and a different matcher. -->
# Two guards match a command keyword inside a quoted string

**Type:** task
**Origin:** ai

## Goal

Make `hooks/flutter-workdir-guard.py` and `hooks/dev-server-guard.py` bind their matches to the
command actually being run, so a keyword sitting inside a quoted string or an unrelated `grep` stops
tripping them.

## Context

Two live false positives, both on 2026-09-04, both during the `/mega-todos` run:

1. **`flutter-workdir-guard.py`** - a plain `Bash` call whose command text merely contained the word
   `flutter` (a `grep` looking for pubspec references) tripped the leading-command check, with no
   `flutter`, `fvm` or `dart` command being invoked.
2. **`dev-server-guard.py`** - a `PowerShell` call that was archiving todos was blocked with
   `looks like a long-lived dev server started directly in the shell (matched: next start)`. The
   phrase `next start` appeared only inside a quoted `-Note` prose string describing what todo 883
   had just changed. Ironic and immediate: 883 (commit `906b709`) is what added `next start` as a
   matched shape, and the very first prose mentioning it tripped the guard.

Both are the same shape as two already-fixed siblings, which is why one pass should cover them:
todo 864 anchored `dev-backend-guard.py`'s `DEV_MARKERS` to a word boundary (commit `9cc117e`), and
todo 881 required the `cargo` token to sit in command position by reusing `COMMAND_START_RE` from
`shell-content-write-guard.py` (commit `cbcc0c9`). **`COMMAND_START_RE` is the reference
implementation** - prefer reusing it over inventing a third approach.

Note both files were touched by todo 893's shared-tokenizer extraction (commit `5403a61`), which
also documented the per-guard ValueError fallback semantics. Read the current state of `_hooklib.py`
before editing.

## Approach

1. Reproduce both first, as `PreToolUse` payloads: a `grep` containing the word `flutter`, and a
   `PowerShell` command carrying `next start` inside a quoted argument. Confirm both deny today.
2. Require the trigger token in command position for both guards, reusing `COMMAND_START_RE` the way
   todo 881 did rather than adding bespoke quote masking.
3. Add a positive and a negative case per guard: a real `fvm flutter run` in the wrong workdir still
   blocks, a real `next start` still blocks, and neither prose form does.

## Acceptance

- A `grep`/`ls` whose text merely contains `flutter` is not blocked.
- A command carrying `next start` only inside a quoted string is not blocked.
- A genuine `flutter`/`fvm`/`dart` command in the wrong working directory still blocks, and a genuine
  `next start` still blocks.
- `python hooks/test_flutter_workdir_guard.py` and `python hooks/test_dev_server_guard.py` pass, and
  `python ci/run_all.py` exits 0.

## Notes

- Filed by /mega-todos on 2026-09-04 from a triage-sweep out-of-scope report.
