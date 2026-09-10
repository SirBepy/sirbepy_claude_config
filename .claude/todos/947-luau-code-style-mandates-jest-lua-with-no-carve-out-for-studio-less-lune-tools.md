<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=EASY, worth=6, reconfirm-count=1, content-hash=5a9cfc80 -->
<!-- duplicate-checked: guard hit done/83-shortcut-skill-rest-fallback.md, which is about a Shortcut API REST fallback and shares only the words "mandates", "with", "tools". Grepped the whole backlog for "jest-lua" and "code-style/luau": the only hits are done/378 and PLAN.md, both about /test's stack routing, neither about the luau.md testing mandate itself. Genuinely distinct. -->
# luau.md mandates jest-lua with no carve-out for Studio-less lune tools

**Type:** task
**Origin:** ai

## Goal

Give `~/.claude/code-style/luau.md`'s testing section an explicit carve-out (or a stated exception
procedure) for Luau that runs under standalone lune rather than inside Roblox, so a project in that
shape is not permanently in silent breach of a global rule it cannot satisfy.

## Context

Surfaced 2026-09-05 by a `/code-check` review inside the `roblox-trend-pipeline` project, during
the run that implemented Plan D phases 4-12. Filed here rather than in that project's backlog
because the gap is in the global `~/.claude` tree, per global CLAUDE.md's rule that a finding about
the global tree belongs in this repo's own backlog.

`~/.claude/code-style/luau.md`'s "Testing Roblox / Luau Code" section mandates jest-lua plus
run-in-roblox, with `describe()` / `it()` / `expect()` from `JestGlobals`.

`roblox-trend-pipeline`'s `rbxl-gen` is Luau, but it is a **standalone lune CLI**: it deserializes
a `.rbxl`, mutates the DOM, and reserializes, never opening Studio. Its suite is a flat
`{ name = fn }` table runner (`tests/rbxl-gen/run.luau` plus `tests/rbxl-gen/helpers.luau`) and is
currently 64 green tests across 10 files. Adopting jest-lua there would mean pulling in
run-in-roblox and Roblox Studio purely to run tests for a tool whose entire selling point is not
needing them.

So the rule as written is unsatisfiable for that project, and the review correctly declined to file
it as a code defect: the new test files match the established local pattern, which predates the
reviewed diff. It is a documentation gap, not a code problem.

This is the "unwritten-rule observations" path in `/code-check` working as intended: the observation
became a doc todo rather than a code todo. Worth noting because that routing is easy to get wrong.

## Approach

1. Read `~/.claude/code-style/luau.md`'s testing section as it currently stands.
2. Add a short carve-out naming the condition, not the project: Luau that runs under standalone
   lune (no Roblox runtime, no Studio) is not required to use jest-lua, since jest-lua's harness
   assumes the Roblox runtime. State what such a project should do instead, at minimum: a
   deterministic runner, one assertion helper module, and tests that run from a single command.
3. Decide whether to name a preferred lune-side runner or leave it to the project. Leaving it open
   is defensible; saying nothing at all is what created this gap.
4. Keep the jest-lua mandate unchanged for anything that actually runs inside Roblox. The carve-out
   is a narrowing, not a weakening.

Rejected: adding a project-specific exception naming `roblox-trend-pipeline`. Global style docs
should key off the technical condition, or the same question resurfaces for the next lune tool.

## Acceptance

- `~/.claude/code-style/luau.md` states, in one readable paragraph, when jest-lua is required and
  when it is not.
- A reader with a lune-only Luau project can tell from the doc alone that they are compliant,
  without needing to ask.
- The existing jest-lua guidance for in-Roblox code is unchanged.
- `python ci/run_all.py` passes.

## Notes

Second data point, 2026-09-05, `C:\Users\tecno\Desktop\Projects\head_soccer_v_fable_oneshot`
(a Roblox game whose deterministic sim also runs headless in Lune 0.10.4): it solved the same gap
by running the SAME `*.spec.luau` files under both runtimes, a hand-rolled jest-compatible shim
for Lune (`lune/jest-shim.luau`, `lune/test.luau`) and real jest-lua in Studio, with a
dual-runtime header per spec (`require(script and game:GetService("ReplicatedStorage").DevPackages.JestGlobals or "../../lune/jest-shim")`).
Worth naming in the carve-out as the shape to prefer when code runs in both places. Three
Luau-toolchain facts found there belong in luau.md's Lune paragraph too, each verified by a
probe in that repo (`game-packages/probe/`, `tests/probe/Rfc.spec.luau`):

- Lune follows the Luau require-by-string RFC: an `init.luau`'s own `./` resolves against the
  PARENT of its folder (the file acts as `pkg.luau` beside the folder), so from `init.luau` its
  children are `@self/Child` and a sibling package is `./sim`; from a plain file, siblings are
  `./Child` and a sibling package is `../sim`. `../` from an init file does NOT reach the
  package's parent.
- selene's `roblox` std types `require` as taking an Instance, so a bare string-literal require
  fails lint as `incorrect_standard_library_use`; `pcall(require, "./X")` and the guarded shim
  `require(script and script.X or "./X")` pass. A custom std that widens `require` is the clean
  fix and is untested.
- Roblox's own support for the bare RFC forms was still UNVERIFIED there (Studio jest blocked
  that day); the shim form is what the repo standardized on.
