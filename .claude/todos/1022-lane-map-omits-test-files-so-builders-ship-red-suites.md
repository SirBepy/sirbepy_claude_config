<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=7, reconfirm-count=1, content-hash=d0b42319 -->
<!-- duplicate-checked: the existing lane-map guidance in mega-todos Step C is about file-overlap partitioning and unverified paths; nothing in it or in delegation-doctrine.md says a todo's owned set must include the tests that assert against the files it moves. 1020 and 1021 are the same run's other findings but different mechanisms (vehicle choice, classifier). -->
# A lane's owned files omit the tests that assert on them, so builders ship red suites

**Type:** skill-improvement
**Origin:** ai
**Priority:** Med

## Goal

A `/mega-todos` builder can fix the test its own change breaks, instead of handing a red suite to the
barrier.

## Context

Cost two barrier repairs on one run, 2026-09-25, in `claude_usage_in_taskbar`. Both were the same
shape and both were the orchestrator's lane-map error, not the builders':

1. **Todo 961** split `projects.ts` into `projects.ts` + `projects-render.ts`.
   `tests/projects_view.test.mjs` does static analysis - it `readFileSync`s `projects.ts` and regexes
   for markup strings (`role="button"`, `id="projects-list"`). The markup moved to the new file, so 5
   of its 21 assertions went red. The builder reported it and could do nothing: `tests/` was not in
   its owned set. The orchestrator fixed it at the barrier (`8666cc7f`).
2. **Todo 958** needed two functions exported from `e2e/view-harness/harness.ts`. That file was not
   in the owned set either, so the builder duplicated the algorithm instead, documented the duplicate
   inline, and reported the acceptance item as unmet. The orchestrator undid the duplicate and did it
   properly at the barrier (`aa6e4956`).

Step C already requires the scout to name every file a fix will WRITE to, existence-check each, and
mark it verified/NEW/unverified. What it does not require is the second hop: **for each file in that
set, which tests assert against it, and does the fix change what they assert?** A static-analysis
test that reads a source file by path is exactly the case a pure file-move breaks and a
behaviour-preserving refactor otherwise would not.

Case 2 is a different miss: the scout listed the files the fix touches, but not the file the fix needs
to CHANGE THE INTERFACE OF. A "share this helper" todo always implies edit rights on wherever the
helper is going to live.

## Approach

Two additions to Step C's scout brief, both mechanical enough to be checkable:

1. **Per todo, grep `tests/` and the e2e directories for each owned path's basename AND for the
   symbols being moved.** Any hit joins that todo's owned set. Cheap: one grep per file. A static
   test that `readFileSync`s a path is the highest-value hit and the easiest to spot.
2. **For a dedupe/share-a-helper todo, the destination module is owned too**, not just the call
   sites. If the destination is another lane's, that is a lane-merge signal - the two todos belong in
   the same lane, sequentially - not a reason to let the builder duplicate.

Also worth considering for the report shape: a builder that finds a test it cannot fix should say so
in a named section the orchestrator drains at the barrier, rather than in free prose where it can be
skimmed past. Both builders here did report it, clearly, so this is a nice-to-have rather than the
fix.

## Acceptance

- [ ] Step C's scout brief requires the test-file grep and states what to do with a hit.
- [ ] Step C states that a share-a-helper todo owns its destination module or merges lanes.
- [ ] A dry run over a backlog containing a file-split todo produces an owned set that includes that
      file's static-analysis test.

## Notes

- /loop-todos 2026-10-05: Step C test-file grep and destination-module ownership shipped in skills/mega-todos/SKILL.md. Only Acceptance item 3 remains: prove it on a real /mega-todos dry run that the owned set picks up the moved file's static-analysis test.

Both repairs were cheap this time because the orchestrator was watching a barrier. In a run where the
barrier is the FINAL one, the same miss ships a red suite.
