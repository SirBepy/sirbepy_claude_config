<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-09-10, complexity=HARD, worth=7, reconfirm-count=4, content-hash=32148d0a -->
<!-- duplicate-checked -->
# Nothing stops a subagent writing into .claude/todos/, and one did

**Type:** skill-improvement
**Origin:** ai

## Goal

Decide whether the doctrine's "a subagent never writes into `.claude/todos/`" rule needs mechanical
enforcement, now that there is a confirmed instance of a subagent ignoring it, and act on the
decision.

## Context

`refs/delegation-doctrine.md`'s "Out-of-scope findings" section states the rule and records that a
hook was **already considered and rejected** for it:

> A PreToolUse write-guard hook was considered and rejected here: it enforces mechanically, but the
> report-back channel keeps the same finding without needing a new harness capability.

That rejection is carried forward here on purpose, per the backlog contract, so this todo is not a
blind re-litigation. What changed is the evidence behind it.

The rejection's premise was that the report-back channel is sufficient. On 2026-08-19, during a
33-agent `/mega-todos` run, a builder **bypassed the report-back channel entirely** and wrote
`.claude/todos/391-builders-have-no-sanctioned-way-to-get-a-whole-tree-baseline.md` directly. Every
dispatch prompt in that run carried the "NEVER write into `.claude/todos/` - report findings, the
orchestrator allocates ids" instruction verbatim.

It got lucky on the id: 391 was genuinely free, so no collision occurred. Todo 291's original
incident (a builder writing `263-...` that collided with an already-taken id inside the same run)
shows what happens when it does not.

Note the finding itself was good and was kept. The channel was the problem, not the content.

## Approach

1. Weigh the two failure modes honestly rather than defaulting to a hook. This repo kills
   guess-based hooks, but this one is not a guess: it is a path-shaped, exact mechanical check
   (`\.claude/todos/.*\.md$` written by a non-orchestrator), which is the category the hook doctrine
   in `PLAN.md` says DOES ship.
2. The blocker is detection: a PreToolUse hook cannot obviously tell an orchestrator's write from a
   subagent's. Establish whether the payload carries anything that distinguishes them before
   designing around it. **If it does not, say so and stop** - an unenforceable rule stays prose, and
   that outcome closes this todo legitimately.
3. If it is enforceable, follow `hooks/todo-duplicate-guard.py`'s shape and ship it with a test.
4. Either way, update the doctrine's recorded rejection with the 2026-08-19 evidence, so the next
   reader sees the rule has been broken in practice rather than only in theory.

## Acceptance

- [x] The doctrine's rejection note reflects the 2026-08-19 instance.
- [ ] Either a guard exists with a test, or the doctrine states plainly why it cannot be enforced.
- [x] No new guess-based hook ships.

## Notes

- **Advanced but NOT finished, 2026-08-31, `/mega-todos` batch 1, commit `441e9d0`.** Deliverable (a)
  landed: `refs/delegation-doctrine.md` now carries the 2026-08-19 evidence (a builder wrote
  `.claude/todos/391-*` directly during a 33-agent run, bypassing the report-back channel, and got
  lucky the id was free, unlike `done/291`'s `263-*` collision), so the old rejection reads as
  tested-and-broken rather than theoretical.
- **What remains is the second acceptance item, and it is genuinely open, not skipped.** The doctrine
  now records that whether a PreToolUse hook can distinguish an orchestrator's backlog write from a
  subagent's is UNRESOLVED, because no `is_subagent`-shaped field appears in the payloads
  `hooks/_hooklib.py:30-35` parses. Settling it needs a deliberate nested-agent probe: dispatch an
  agent, have it attempt a Write into the backlog, and capture what the hook actually receives. The
  orchestrator withheld that probe from an unattended builder on purpose, since a nested dispatch
  inside a 44-agent run is the wrong place to run an experiment.
- Next run: do the probe FIRST. If the payload distinguishes them, ship the guard shaped like
  `hooks/todo-duplicate-guard.py` plus a test. If it does not, change the doctrine's "unresolved" to
  a settled "cannot be enforced at the hook layer" and close this out.

### PROBED 2026-09-10 (/loop-todos cycle 4) - the open question is answered, the guard is not built

The question this todo was stuck on is settled: **a PreToolUse hook CAN tell a subagent's write
from the orchestrator's.** The payload carries `agent_id` and `agent_type` if and only if the call
comes from a dispatched agent.

Evidence, both halves captured the same way (temporarily instrument `hooks/todo-duplicate-guard.py`
behind a marker file, fire a Write whose numeric id is guaranteed to collide so nothing is ever
created, revert the hook after):

- A dispatched builder's own denied Write carried `agent_id` and `agent_type`. An agent that
  builder itself dispatched carried a DIFFERENT `agent_id` under the same `session_id`, so the
  field discriminates at any nesting depth, not just one level down.
- The orchestrator's own denied Write, fired from the top-level session, carried **neither key**.
  Its full payload was exactly: `session_id`, `transcript_path`, `cwd`, `prompt_id`,
  `permission_mode`, `effort`, `hook_event_name`, `tool_name`, `tool_use_id`.

The builder that ran the first half correctly refused to ship a guard without the second, because
without the top-level baseline an `agent_type`-gated denial might have blocked the orchestrator's
own legitimate `/create-todo`, `/close` and `/code-check` writes. That baseline now exists.
`refs/delegation-doctrine.md`'s paragraph has been corrected accordingly.

**Remaining work, now small and fully specified:**

1. A PreToolUse hook on `Write` matching `\.claude/todos/\d+-.*\.md$` that denies when `agent_id`
   is present in the payload, with a message pointing at the "Out-of-scope findings" report channel
   as the correct route.
2. The `done/` and `.claims/` paths must NOT match, same path shape `todo-duplicate-guard.py`
   already implements in `todos_target_dir` - reuse that function rather than writing a second
   matcher.
3. A test in `hooks/test_*.py` covering both directions: a payload carrying `agent_id` is denied, an
   otherwise identical payload without it is allowed.
4. Check whether any legitimate flow has a subagent write a todo before shipping. The doctrine says
   none does, and `/mega-todos` builders commit but file findings through their report, but that is
   a claim worth one grep rather than an assumption.
- Fixed 2026-09-11 (/loop-todos): hooks/agent-todo-write-guard.py, wired PreToolUse on Write|Edit, with hooks/test_agent_todo_write_guard.py (14 cases) discovered by CI, taking the hook suite count from 32 to 33. The builder re-verified the agent_id premise live against CLI 2.1.261 rather than trusting the one-day-old record, using a non-blocking diagnostic build, and incidentally captured the orchestrator's own concurrent Write of todo 981 as the negative case: same session_id, no agent_id key at all. Path matching reuses todo_duplicate_guard's todos_target_dir unmodified, which is also why a subagent's .claims/ write and heartbeat are unaffected - those carry an extra path segment and never match. The orchestrator then probed the wired guard independently with four synthetic payloads: subagent backlog write denied (exit 2, message naming the Out-of-scope findings channel), orchestrator write allowed, subagent claim write allowed, subagent write outside todos allowed. refs/delegation-doctrine.md's paragraph claiming the guard was not yet built was corrected in the same commit.
