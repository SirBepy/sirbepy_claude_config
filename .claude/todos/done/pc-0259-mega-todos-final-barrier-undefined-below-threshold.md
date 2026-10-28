<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-12, complexity=EASY, worth=8, reconfirm-count=1, content-hash=1ff567d6 -->
# `/mega-todos` verify ladder undefined for a run that ENDS below the 10-15 todo threshold

**Type:** skill-improvement
**Origin:** ai

## Goal

`~/.claude/skills/mega-todos/SKILL.md` Step D defines a per-batch barrier and a full floor "every
10-15 completed todos", but says nothing about the LAST barrier of a run. A short run therefore has
no defined stopping check, and the ambiguity is expensive in exactly one direction.

## Context

Observed 2026-08-11 in `claude_usage_in_taskbar`. A `/mega-todos` run was scoped by the dev to 7
Rust split todos. Measured wall clock, from the dev's scope answer to done: **94 minutes**, of which
the 7 parallel builders were **6 minutes** and the verification barrier was **~65 minutes**.

The orchestrator ran the FULL floor (`cargo check --all-targets`, `pnpm tsc --noEmit`, `cargo test
--lib`, `cargo test --test export_types`, `cargo build`) on a 7-todo batch. Step D's ladder only
called for `cargo check` + `pnpm tsc --noEmit` at that size; the full floor is specified for "every
10-15 completed todos". The correct barrier would have been roughly 10 minutes.

Two compounding costs, both worth naming in the skill:

1. **The threshold reads as a floor, not a ceiling.** With a run ENDING at 7 todos, "this is the
   last barrier, so do the thorough one" is a natural and defensible misread. The skill should say
   which it wants.
2. **The four cargo invocations barely share artifacts.** `cargo check --all-targets`, `cargo test
   --lib`, `cargo test --test export_types` and `cargo build` build different artifact sets -
   `check` produces no codegen `build` can reuse. Running all four serially is close to four builds
   of the same tree. `cargo test --lib` alone was 180s of test execution on top of its compile.

The dev's reaction was "you took like an hour just to do 7 todos?" - the run's correctness was never
in question (883 tests green, zero barrier failures, zero repair passes), only its cost.

Related: `claude_usage_in_taskbar` memory `project_parallel_lanes_no_cargo_shared_target_lock`,
which records why builders must not run cargo at all in a parallel run.

## Approach

In `~/.claude/skills/mega-todos/SKILL.md`, Step D's "Verify ladder" section:

1. State explicitly what the FINAL barrier of a run is, independent of todo count. Proposed: the
   final barrier is the same cheap ladder (`cargo check --all-targets` + `pnpm tsc --noEmit`) unless
   the full floor has not run for 10+ completed todos, in which case run it once at the end.
2. Note that the full floor's commands do NOT share build artifacts, so it is a multiple of a single
   build, not an increment on the cheap ladder. An orchestrator that does not know this will
   reasonably assume the extra commands are nearly free once `cargo check` has warmed the cache.
3. If both a test run and a build are genuinely wanted, prefer `cargo test --lib` alone - it already
   compiles the lib - over pairing it with a separate `cargo build`.

Rejected: making the full floor unconditional at the end of every run. That is exactly the behavior
that cost 55 minutes here, and a `cargo check --all-targets` that passes has already proven every
target compiles.

## Acceptance

- Step D names the final-barrier rule in one sentence, with no todo-count ambiguity.
- A future run of fewer than 10 todos finishes its barrier in one cargo invocation plus `pnpm tsc`.
- The artifact-sharing caveat is written down, so the cost is not rediscovered by measurement again.

## Notes

- Done 2026-08-12, commit c930934. Final-barrier rule stated explicitly (cheap check, not the full floor, unless the floor has not run for 10+ todos) with the 94-minute measurement, plus the cargo artifact-sharing caveat.
