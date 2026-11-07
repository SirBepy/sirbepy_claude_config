<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: no existing todo parallelizes the gate steps -->
# Push gate steps run in parallel

**Type:** task
**Origin:** dev
**Summary:** The gate's independent steps (code-check review, unit tests, build for e2e) start together instead of one after another.

## Goal
`/commit`'s Pre-push gate and `/release` start the code-check subagent, the local unit-test run and the build that e2e needs at the same time, then join on all three before `mark`.

## Context
Release 0.2.146 ran them in series: code-check about 2 min, build about 4 min, wdio sweep several min, plus the new unit-test run (up to 7.5 min cold). Code-check is read-only and unit tests and the build share a cargo target dir, so tests and build must be serialized with each other but not with code-check.

## Approach
Dispatch code-check in the background first, then run test and build in order while it works; wdio follows the build. Keep the join explicit so a red code-check still blocks `mark`.

## Acceptance
Wall-clock gate time drops by about the length of the shorter of code-check and the build, with the same pass/fail verdicts.
