<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-06, complexity=HARD, worth=8, reconfirm-count=6, content-hash=589349fb -->
<!-- duplicate-checked -->
# The testing floor is a rule Claude must remember, not a gate it cannot pass

**Type:** task
**Origin:** ai

## Goal

Make the verify floor mechanically unbypassable for code changes, using a Stop hook that blocks the
turn from ending while the project's fast checks fail.

## Context

Found in the 2026-08-19 harvest (`refs/harvest-2026-08-20-oss-claude-repos.md`).

CLAUDE.md's "Testing & verification floor" says every fast check the project has must pass before
claiming done, with no size exemption. It is prose. Compliance depends on the model remembering it,
and the same class of rule has demonstrably failed repeatedly here: the em-dash ban needed a Stop
hook after being restated verbatim in every dispatch of a run that broke it three times anyway (todo
290), and the unverified-mechanism rule recurred five times despite being memory-documented after each
one (recorded in CLAUDE.md itself).

**A Stop hook is the only mechanism that can guarantee something runs before a turn ends.** That is
already proven in this repo: `em-dash-guard.py` and the ui-screenshot reminder are Stop hooks, and
they work. The floor is a bigger rule than either and has no equivalent enforcement.

Reference implementation: `repos/brain-bootstrap_claude-code-brain-bootstrap/dot-claude/hooks/tdd-loop-check.sh`.
A Stop hook that exits 2 (blocking turn end) while tests, lint or typecheck fail, with three design
decisions worth copying exactly:

1. **Capped at 25 iterations**, so a genuinely broken project cannot trap the session in a loop. The
   documented harness cap on consecutive Stop blocks is 8, so the real ceiling may be lower; verify.
2. **Activated only via a session-scoped flag file** written when SOURCE files were edited, not config
   files. This is the critical part: without it, every conversational turn tries to run the test suite.
3. Source-versus-config discrimination, so editing a `tsconfig.json` does not trigger a full run.

Directly relevant hazard from this repo's own history: process hygiene. An unbounded test run from a
Stop hook is exactly how 90+ orphan vitest processes once pegged the CPU at 100% and 90°C. The
concurrency cap (5) and the orphan-check requirement in `refs/process-hygiene.md` are non-negotiable
here, and a Stop hook that spawns test processes is the highest-risk place in the whole repo to get
that wrong.

Depends on todo 426 for the `Stop` + `"decision": "block"` JSON form, which gives Claude a structured
reason instead of a bare exit code. Exit code 2 works without it, so this is not blocked, but the
JSON form is better.

## Approach

1. Establish the real cap on consecutive Stop blocks in this harness version before designing the
   loop. Docs say 8; `brain-bootstrap` uses 25. Whichever is true bounds the design, and a hook that
   assumes the wrong number either traps a session or gives up early.
2. Solve the activation gate first, because it is what makes this safe. A session-scoped flag file
   written by a PostToolUse hook when a source file is edited, cleared at session start. Define
   "source file" concretely per stack, and exclude markdown, config, todos, and this repo's own
   skills and refs. **Most turns in this repo edit prose and must not trigger anything.**
3. Detect the project's fast checks rather than hardcoding them. `/test` already infers the stack;
   reuse that inference rather than writing a second one that drifts.
4. Enforce process hygiene inside the hook, not as an afterthought: concurrency cap 5, explicit
   timeout, and an orphan check after the run. A Stop hook that leaves orphans runs on every turn end,
   so it compounds faster than anything else here.
5. Make the escape hatch explicit and documented. There must be a way for the dev to end a turn with
   failing checks (a flag, an env var, a phrase), because sometimes the right move is to stop with
   the failure visible. A gate with no escape gets disabled entirely, which is worse.
6. Test the loop bound by pointing it at a deliberately failing project and confirming it stops
   blocking rather than looping forever.

## Acceptance

- The consecutive-Stop-block cap is established empirically and the hook respects it.
- A prose-only turn (editing a `.md` file) does NOT trigger any check. Verified by observation.
- A source-file turn with failing checks IS blocked, and the block reports which check failed.
- The escape hatch works and is documented.
- Orphan check after a triggered run pastes real process output proving nothing survived.
- A deliberately unfixable failure terminates at the cap instead of looping.
- All existing Stop hooks (`em-dash-guard.py`, ui-screenshot reminder) still fire correctly.

## Notes

- Phase 0 answer (Joe): wire the testing-floor Stop gate now, Joe watching; verify a few turns still end after wiring. (2026-10-07, /loop-todos Phase 0)

This is the highest-risk todo in the harvest set. A misfiring Stop hook affects every single turn,
and the failure mode is a session that cannot end. Build the activation gate and the escape hatch
before the check-running logic, not after.

Do not run e2e or Playwright from this hook. CLAUDE.md explicitly keeps slow suites out of the floor,
and a Stop hook is the worst possible place to violate that.

### BUILT but deliberately NOT WIRED, 2026-09-11 (/loop-todos cycle 4)

The gate exists, is tested, and is switched off. Wiring it is the one step left, and it was withheld
on purpose: this is a `Stop` hook, so if it is wrong every concurrent session on the machine loses
the ability to end a turn at once. There were four live sessions and the dev was away, so nobody
could switch it back off. The artifact is safe to sit unwired; switching it on wants a human watching
the first few turns.

**Shipped, all under `hooks/`, none referenced from `settings.json`:**

- `_testing_floor_lib.py` - shared helper, fully injectable: stack detection, source-file classifier,
  state read and write, escape-hatch resolvers, subagent detection.
- `testing-floor-flag.py` - the `PostToolUse` activation-gate writer.
- `testing-floor-guard.py` - the `Stop` blocking gate.
- `test_testing_floor_flag.py` (17 unit, 7 integration) and `test_testing_floor_guard.py` (14 unit,
  5 subprocess, 2 real-detection). Both green, both discovered by CI, which went 34 suites to 37.

**Escape hatch, built first, before any blocking logic existed.** Set `CLAUDE_TESTING_FLOOR_SKIP` to
any truthy value, or create `hooks/.testing-floor-skip`, and the hook exits 0 unconditionally. It is
checked before any state is read, so a stuck session is freed without a `settings.json` edit and
without knowing a phrase it has never seen.

**Activation gate, built second.** The flag file is written only when the turn's own
Edit/Write/MultiEdit/NotebookEdit touched a path the source classifier recognises. A read-only turn,
a markdown-only turn, or a turn that only searched never reaches the blocking logic at all.

**Subagent exclusion** reuses `agent-todo-write-guard.py`'s own `is_agent_call` by import rather than
reinventing the `agent_id` check. A builder has its own verify floor and is not the target.

**Both directions exercised against a real, unstubbed check**, not only the happy path: a genuinely
failing `ci/run_all.py` blocks the turn, a genuinely passing one allows it and clears the flag.

**Fail-open** is a single boundary in `main()`; every unexpected exception exits 0, proven by four
subprocess cases including fault injection.

### The remaining work

1. **Wire it**, when the dev is present. The exact block, to be MERGED into the existing
   `PostToolUse` and `Stop` arrays rather than replacing them:

   - `PostToolUse`, matcher `Edit|Write|MultiEdit|NotebookEdit`, command
     `python "C:\Users\tecno\.claude\hooks\testing-floor-flag.py"`.
   - `Stop`, no matcher, command
     `python "C:\Users\tecno\.claude\hooks\testing-floor-guard.py"`.

2. **Confirm the real retry cap.** This todo's own Approach step 1 asked for the harness's true
   ceiling on consecutive `Stop` blocks to be established empirically. It could not be: measuring it
   requires the hook to be live. The docs and the harvested reference implementation disagree (8 vs
   25), so the cap defaults to a conservative 3, under either candidate. Confirm it when wiring.

3. **Two design tradeoffs worth the dev's eyes**, both deliberate and documented in the code: the
   Node concurrency cap is enforced as a post-run orphan sweep rather than by injecting a
   `--maxWorkers` flag into an unknown test script, and a Roblox or Luau project is detected but
   never executed, because a hook cannot invoke the `/jest-lua` skill; it reports and passes through.

4. **`detect_stack()` runs only ONE stack, so the gate cannot enforce the floor it exists for.**
   Found 2026-09-12 by an independent `/code-check` reviewer that did not write the code, and
   reproduced rather than argued: a scratch directory holding both `Cargo.toml` and `package.json`,
   the exact Tauri shape `skills/test/SKILL.md` names, makes `hooks/_testing_floor_lib.py:166`
   return only `('rust', ...)`. The Node half is never run.

   `skills/test/SKILL.md` Step 1 is explicit: "A repo can match more than one row (a Tauri app
   matches Rust *and* Node); run every row it matches." `detect_stack()` instead returns a single
   `(label, argv)` tuple and stops at the first hit in a fixed priority order. The module's own
   docstring claims it "mirrors skills/test/SKILL.md's own table (same rows, same precedence)", but
   `/test` has no precedence concept when several rows match, so the docstring overclaims a parity
   the code does not have.

   This matters more here than in an ordinary helper: CLAUDE.md's testing floor says "every FAST
   check the project HAS", and this hook exists specifically to enforce that floor at Stop time. A
   floor gate that silently checks one of two stacks would pass a turn that broke the other.

   Fix: have `detect_stack()` return a LIST of matches and have `run_checks()` run each and
   aggregate (`ok = all(...)`, summaries joined). That is a real API decision, not a one-liner, since
   it changes the return shape of `detect_stack`, `run_stack_check` and `run_checks` and raises the
   question of what a combined Roblox-plus-Node message should say. If single-stack is instead a
   deliberate simplification for an unwired prototype, narrow the docstring to say first-match only,
   rather than leaving it claiming parity.

   No existing test would catch this: both suites build single-stack or stubbed fixtures only. The
   regression test to add is a temp dir with two stack markers and distinguishable injected results,
   asserting the summary names BOTH. It fails today and passes after the fix.
- loop-todos cycle 2, 2026-10-06: the dual-stack defect above is fixed. `detect_stack()` returns a list, `run_checks()` runs every matched stack and aggregates (ok = all, summaries joined), regression test `dual_stack_checks()` in hooks/test_testing_floor_guard.py RED then GREEN. Still unwired; the wiring question is in Open questions.
