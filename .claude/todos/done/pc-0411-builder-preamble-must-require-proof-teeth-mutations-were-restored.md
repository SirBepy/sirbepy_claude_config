<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-29, complexity=EASY, worth=8, reconfirm-count=2, content-hash=633e95ff -->
# Builder preamble must require proof that teeth-mutations were restored

**Type:** skill-improvement
**Origin:** ai

## Goal
Make `~/.claude/refs/builder-preamble.md` force a builder that mutated production
code to prove the mutation is gone, so an interrupted or sloppy dispatch cannot
leave dead code behind that still passes tests.

## Context
2026-08-19, revaire-mobile REV-5312. A builder dispatch was told to verify its new
tests had teeth (mutate the production code, watch the test fail, restore). The
dispatch was interrupted mid-run. It left the mutation live:

```dart
Widget _selectedBundleLabel(EphemeralBundle bundle) {
  final label = bundle.label ?? bundle.environmentId;
  if (true) return _selectedLabel(label);   // <-- mutation, never restored
  ...unreachable...
}
```

The whole P1 fix was unreachable. `flutter analyze` was clean and the dialog test
file passed, because the tests asserting the new behaviour had not been written
yet at the moment the mutation went in. Nothing in the verify floor could see it.
It was caught only because the dev interrupted out of unrelated nervousness and
the orchestrator then read the file.

The current preamble (`refs/builder-preamble.md`) has no clause about this, and
the doctrine's "Quality tells" section does not list it either. The failure is
silent by construction: a mutation that disables a feature makes tests MORE
likely to pass, not less.

## Approach
Add to the static block in `~/.claude/refs/builder-preamble.md`, so it is
unconditional body text rather than a placeholder a hurried reader can drop:

- If you mutated any non-test file to prove a test fails, restore it and paste
  `git diff HEAD -- <that file>` in your report, showing the mutation is absent.
- Never leave a `if (true)`, `if (false)`, early `return`, or commented-out guard
  in a non-test file. State explicitly in the report that you checked.

Then add a matching grep to the orchestrator's side in
`~/.claude/refs/delegation-doctrine.md`'s "Quality tells": after any dispatch that
reported a teeth-check, grep the changed non-test files for `if (true)`,
`if (false)`, and `// TEETH`-style markers before accepting the report.

## Acceptance
- `refs/builder-preamble.md` contains the restore-and-prove clause in its static
  paste block.
- `refs/delegation-doctrine.md` "Quality tells" names the post-dispatch grep.
- A dispatch prompt generated from the preamble visibly carries the clause.

## Notes

- Done via /mega-todos batch 1, commit 60884c4: refs/builder-preamble.md requires a builder that mutated a non-test file to restore it and paste git diff HEAD proving the mutation is absent, and refs/delegation-doctrine.md Quality tells now has the matching post-dispatch grep check.
