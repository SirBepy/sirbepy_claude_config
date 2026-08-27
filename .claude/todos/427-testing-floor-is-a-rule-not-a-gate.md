<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-08-27, complexity=HARD, worth=4, reconfirm-count=1, content-hash=589349fb -->
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

This is the highest-risk todo in the harvest set. A misfiring Stop hook affects every single turn,
and the failure mode is a session that cannot end. Build the activation gate and the escape hatch
before the check-running logic, not after.

Do not run e2e or Playwright from this hook. CLAUDE.md explicitly keeps slow suites out of the floor,
and a Stop hook is the worst possible place to violate that.
