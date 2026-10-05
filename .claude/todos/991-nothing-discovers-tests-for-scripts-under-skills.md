<!-- Claim before executing: .claude/todos/.claims/991-nothing-discovers-tests-for-scripts-under-skills.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=6, reconfirm-count=1, content-hash=c66f26b5 -->
<!-- duplicate-checked -->
<!-- checked against 977 and 983, both in done/. 977 added a test for tools/dead-probe-check.py,
     which ci/run_tool_tests.py already discovered; it never touched discovery itself. 983 changed
     commit-pathspec.sh, whose tests ARE discovered via the skills/commit/test_*.sh glob. Neither
     is about the directories that have no discovery at all. -->
# Scripts under skills/ have no test discovery, so a test written there would never run

**Type:** task
**Origin:** ai

## Goal

Decide whether `ci/run_all.py` should discover tests for executable scripts living under `skills/`,
and either wire it or write down that it deliberately does not.

## Context

Raised independently by two different agents on 2026-09-11 and 2026-09-12, neither aware of the
other, which is why it is filed rather than shrugged off.

`ci/run_all.py` discovers:

- `hooks/test_*.py` via `run_hook_tests.py`
- `tools/test_*.py` via `run_tool_tests.py`
- `skills/commit/test_*.sh`, hardcoded to that one directory

Nothing discovers anything else under `skills/`. The consequence is not theoretical:

- The agent fixing todo 975 checked before adding a test for `skills/close/safe-remove-worktree.ps1`,
  found no discovery would reach it, and correctly declined to add a file nothing would ever run.
  That script exists because of a real 2026-07-31 data-loss incident and its fallback chain had been
  unreachable for weeks without anything noticing.
- A `/code-check` reviewer separately flagged that `skills/close/archive-and-commit-todo.ps1` (244
  lines, new, drives real git history) and `skills/mega-todos/build-dispatch.ps1`'s new
  `-CommitMode Barrier` branch both shipped with zero automated coverage for the same reason. Both
  were hand-verified against scratch repos instead, which works once and never again.

So the repo has a real pattern: non-trivial executable logic under `skills/`, verified by hand at
authoring time, with no regression net afterwards. `skills/commit/test_*.sh` proves the shape is
workable; it is simply not generalised.

There is a genuine argument for the status quo, which is why this is a decision and not a bug: most
of `skills/` is prose, a broad glob would be mostly misses, and PowerShell scripts need a different
runner than the `.sh` and `.py` suites. Say which way it goes rather than leaving it implied.

## Approach

1. Count the population first. List every executable file under `skills/` (`.ps1`, `.sh`, `.py`,
   `.mjs`) and how many already have a sibling test. That number decides whether this is worth
   machinery at all; if it is three files, a glob is over-engineering.
2. If wiring it: extend discovery to `skills/**/test_*.{sh,py}` rather than adding a second
   hardcoded directory, and decide separately whether PowerShell gets a runner (Pester is the
   obvious candidate and is a real dependency decision, not a free one).
3. If declining: say so in `ci/run_all.py` next to the existing hardcoded `skills/commit` glob, so
   the next person who wonders finds the answer where they are already looking, and note what to do
   instead (hand-verification at authoring time, recorded in the commit).
4. Either way, name what happens to the two scripts already identified as uncovered. Leaving them
   uncovered is an acceptable answer; leaving it unstated is not.

## Acceptance

- The population count exists and the decision cites it.
- Either discovery reaches at least one previously-undiscovered script's test and that test runs in
  `python ci/run_all.py`, or `ci/run_all.py` carries a written reason it does not.
- No existing suite's discovery changes shape or count as a side effect.
- `python ci/run_all.py` passes.

## Notes

- Do not add a test file anywhere discovery does not reach. That is what produced the confusion this
  todo exists to settle: a file that looks like coverage and is inert.
- Suite discovery here is TRACKED-FILE based. An untracked `test_*.py` is silently not run, which
  cost a wrong suite count during the 2026-09-11 run. Whatever is wired, check it against a staged
  file, not just a written one.
