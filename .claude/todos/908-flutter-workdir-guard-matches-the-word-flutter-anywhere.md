<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: todo 864 is the same substring-matching SHAPE but on hooks/dev-backend-guard.py's DEV_MARKERS; this is a different hook and a different matcher. -->
# flutter-workdir-guard matches the word flutter anywhere in a command

**Type:** task
**Origin:** ai

## Goal

Make `hooks/flutter-workdir-guard.py`'s leading-command check bind to the actual command being run,
so the literal word `flutter` inside an unrelated `grep`, `ls` or quoted string stops tripping it.

## Context

Observed 2026-09-04 during the `/mega-todos` triage sweep: a plain `Bash` call whose command text
merely contained the word `flutter` (a `grep` looking for pubspec references) tripped the guard's
leading-command check, even though no `flutter`, `fvm` or `dart` command was being invoked.

This is the same failure SHAPE as todo 864 (`hooks/dev-backend-guard.py` matched `.env.device` on
the `.env.dev` marker, fixed 2026-09-04 in commit `9cc117e`) but on a different hook with a different
matcher, so 864's fix does not cover it. 864's builder was explicitly asked whether its fix
generalised and reported that this file was outside its lane.

Note `hooks/flutter-workdir-guard.py` is also touched by todo 893 (shared tokenizer extraction), so
check the current state of its `tokenize` and its ValueError fallback before editing.

## Approach

1. Reproduce first: feed the guard a `PreToolUse` payload whose command is a `grep` containing the
   word `flutter` and confirm it denies.
2. Anchor the check to the command position, the same way 864 anchored `DEV_MARKERS` to a path or
   word boundary. Reuse 864's approach in `hooks/dev-backend-guard.py` as the reference shape.
3. Add both a positive case (a real `fvm flutter run` in the wrong workdir still blocks) and the
   negative case above to `hooks/test_flutter_workdir_guard.py`.

## Acceptance

- A `grep`/`ls` whose text merely contains `flutter` is not blocked.
- A genuine `flutter`/`fvm`/`dart` command in the wrong working directory still blocks.
- `python hooks/test_flutter_workdir_guard.py` passes and `python ci/run_all.py` exits 0.

## Notes

- Filed by /mega-todos on 2026-09-04 from a triage-sweep out-of-scope report.
