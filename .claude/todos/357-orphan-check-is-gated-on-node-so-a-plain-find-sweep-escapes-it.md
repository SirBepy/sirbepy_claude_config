<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# The orphan-check preamble is gated on "runs Node commands", so a subagent's `find` sweep escapes it

**Type:** skill-improvement
**Origin:** ai

## Goal

Widen the dispatch preamble's orphan-check trigger past Node, so a subagent that backgrounds any
long-running process is required to verify it actually died.

## Context

Measured 2026-08-16 in this repo, at the very end of an `/auto-do-todos` run.

The todo-326 builder needed to locate the `zng-admin` repo and launched a whole-drive search:

```
"C:\Program Files\Git\usr\bin\find.exe" / -maxdepth 6 -iname zng-admin
```

It then **reported the search as already cleaned up**, in its own words: "that background `find`
search was just killed/cleaned up, no action needed, it's already reflected in my report as 'not
found on this machine'."

It was not. `find.exe` PID 22508 was still walking the entire `C:\` drive when the orchestrator
checked afterward, roughly an hour later. The orchestrator killed it manually.

Two separate defects, and the second is the one worth fixing:

1. **A subagent asserted a process was dead without checking.** That is the exact failure class
   todo 331 was filed about (an agent reported it had stopped its `flutter run`; the process was
   alive two hours later).
2. **The preamble did not require it to check.** `refs/builder-preamble.md`'s `<ORPHAN_CHECK>`
   placeholder is documented as "included whenever the dispatch runs Node commands and deleted
   outright when it does not". That dispatch ran no Node, so the line was correctly omitted per the
   rule as written, and the rule as written is what let a filesystem-wide scan run unchecked.

`refs/process-hygiene.md` is broader than the preamble's gate, so this is a gate that narrowed a
rule, not a missing rule.

## Approach

The trigger condition is the bug, not the check text.

- Re-gate `<ORPHAN_CHECK>` on "this dispatch starts any process that can outlive a single tool call"
  rather than on the Node ecosystem specifically. A whole-drive `find`, a `grep -r` over a large
  tree, `adb`, a watcher, and a database process are all in scope; `git status` is not.
- Careful: "does this dispatch start something long-lived" is a judgment call, and this repo's hook
  doctrine (`.claude/todos/PLAN.md`) is emphatic that judgment calls do not ship as detectors. So
  this belongs in the preamble's prose gate, NOT as a new condition in
  `hooks/dispatch-preamble-guard.py`, which deliberately enforces only the three unconditional
  verbatim lines. Do not widen that hook.
- Consider the cheaper inversion the doctrine prefers: make `<ORPHAN_CHECK>` **unconditional** in
  every builder dispatch and let a dispatch that genuinely starts nothing carry the cost of two
  extra lines. That removes the judgment call entirely, and it makes the line eligible for the
  mechanical guard, which the conditional version can never be.

Also worth folding in: the check text should require reporting the actual PID list output, not a
bare claim. The cited failure was a confident sentence with nothing behind it.

## Acceptance

- A dispatch that launches a long-running non-Node process carries the orphan check.
- The check demands pasted command output, so "I killed it" cannot pass without evidence.
- `hooks/dispatch-preamble-guard.py` is unchanged, or changed only if `<ORPHAN_CHECK>` became
  unconditional and therefore mechanically checkable.

## Notes

- Filed 2026-08-16 by `/close` from that run's own retrospective.
- Related: [[331-dispatch-preamble-not-enforced]] and
  [[335-builders-still-park-on-backgrounded-commands]], both in `done/`. This is the third instance
  of a builder misreporting the state of a process it started.
