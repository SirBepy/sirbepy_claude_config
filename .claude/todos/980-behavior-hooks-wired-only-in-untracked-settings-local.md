<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
<!-- checked against 452 (done/, archived 2026-09-11) and 426. 452 is whether a per-turn reminder
     for custom output styles exists at all; that hook now exists, and this todo is only about WHERE
     it is wired. 426 is about which hook EVENTS are wired (PreCompact, PermissionRequest) and about
     adopting JSON control fields, not about the tracked/untracked split. Different question. -->
# A behavior-enforcing hook wired only in settings.local.json does not survive a re-clone

**Type:** task
**Origin:** ai

## Goal

Decide which side of the tracked/untracked settings split each behavior-enforcing hook belongs on,
and move the ones that belong in version control.

## Context

Found 2026-09-11 while archiving todo 452. That todo shipped `hooks/output-style-reminder.py`, whose
whole purpose is to stop the Silent output style fading over a long session. The file itself is
tracked, but its wiring is not:

- `grep -c output-style-reminder settings.local.json` -> 1
- `grep -c output-style-reminder settings.json` -> 0

`settings.local.json` is deliberately untracked and its own `description` says so, so this is not an
oversight in that file. The question is which side this particular hook belongs on. A hook whose job
is to enforce a global behavior rule is only as durable as its wiring: on a fresh clone of this repo
the file arrives and never fires, and nothing reports that. The hook looks present in `hooks/` and is
silently inert.

There is direct precedent for the tracked side being the right answer. Todo 415 (done, 2026-08-20)
moved the impeccable and status-marker-guard wiring out of `settings.local.json` into the tracked
`settings.json` for exactly this reason, and made `settings.local.json` state its own scope. That
move was never applied to hooks added afterwards.

The general shape matters more than this one hook: nothing checks that a tracked `hooks/*.py` is
wired anywhere at all, so the next behavior hook added to `settings.local.json` has the same fate.

## Approach

1. Enumerate every entry in `settings.local.json`'s hook blocks and every `hooks/*.py` in the repo,
   and diff the two against `settings.json`. Produce the actual list before deciding anything: a
   tracked hook file with no tracked wiring is the population of interest, and its size is unknown.
2. Classify each by the test 415 already implies: does this hook enforce a rule that should hold on
   any machine this repo is cloned to, or is it genuinely machine-local (a path, a personal
   preference, a device)? Machine-local stays put.
3. Move the wiring for the first group into `settings.json`, preserving matcher shape exactly. Do
   this in one complete `Write` per file, never partial edits: concurrent sessions load this file on
   every tool call and a half-written `settings.json` breaks all of them.
4. Consider a `ci/` check that fails when a tracked `hooks/*.py` has no wiring in either settings
   file. That is what would have caught this without a person noticing. Decide whether the check is
   worth its false-positive surface (a hook deliberately parked unwired) and say which way you went.

## Acceptance

- The tracked/untracked classification is stated per hook, not just applied.
- `hooks/output-style-reminder.py` is wired somewhere the wiring is version controlled, or there is
  a written reason it should stay machine-local.
- No matcher changes shape during the move; every moved hook still fires, proven by a real trigger
  rather than by reading the JSON back.
- `python ci/run_all.py` passes.

## Notes

- `settings.local.json` is untracked by design. This todo does not propose tracking that file; it
  proposes moving specific entries out of it.
- Do not widen this into a general settings refactor. The population is "tracked hook file, untracked
  or absent wiring", and nothing else.
