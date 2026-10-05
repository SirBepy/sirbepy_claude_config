<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=EASY, worth=8, reconfirm-count=1, content-hash=3f311728 -->
<!-- duplicate-checked: grepped this backlog and done/ for "claim" crossed with "autopilot|dispatch|builder". 1006, 1011, 1018 and 1020 are about builder preambles and todo WRITES; none covers the orchestrator claiming a todo before a builder EXECUTES it. -->
# /autopilot and the delegation doctrine never tell the orchestrator to claim a todo before dispatching its builder

**Type:** skill-improvement
**Origin:** ai
**Priority:** Medium

## Goal

A todo executed by a dispatched builder is claimed first, on every path, as the global rule requires.

## Context

Root `CLAUDE.md`: *"Claim rule (non-negotiable): before EXECUTING any todo, claim it via
`.claude/todos/.claims/<id>.claim` per the contract - every path, including ad-hoc 'do todo 07'."*

Neither `skills/autopilot/SKILL.md` nor `refs/delegation-doctrine.md` says to do this. Checked
2026-09-29: the only `claim` hits in either file are unrelated (autopilot line 72 is "verify before
claiming done"; line 85 mentions claim rules only for todos *written* at the context hard stop). The
doctrine's dispatch discipline section lists everything a builder prompt must embed and never says the
orchestrator claims the source todo first.

**What happened.** A `/autopilot` run in `claude_usage_in_taskbar` on 2026-09-28 dispatched builders
against todos `989` and `990` and shipped both (`88b1d252`). Neither was ever claimed. It surfaced only
when `close/complete-todo.ps1` archived them and warned *"todo 989 is being completed with no claim on
record"* - after the fact, for every id the run touched. A peer session was live in that same working
tree throughout, which is precisely the case claims exist to protect. Nothing collided, by luck.

The gap is structural, not a slip: an orchestrator following autopilot and the doctrine exactly as
written would skip the claim every time, because neither document mentions it.

## Approach

1. Add the claim to the doctrine's dispatch discipline, since `/autopilot`, `/delegate` and anything
   else that adopts the doctrine inherits it from one place: before dispatching a builder whose work
   comes from a todo, the orchestrator claims that todo via `claim-todo.ps1`; after the report lands
   and the work is committed, it releases via `complete-todo.ps1`, or releases without completing on
   an abort.
2. The orchestrator owns the claim, not the builder. Subagents cannot reliably reach `.claude/todos/`
   (`hooks/agent-todo-write-guard.py` exists precisely to stop them writing there), and the claim has to
   outlive the builder anyway.
3. Consider whether `complete-todo.ps1`'s warning should be louder. It currently prints "Not blocking"
   and the run carries on; that is correct for a lone slip, but it is the only mechanical signal this
   gap produces and it fires only after the work shipped.

## Acceptance

- `refs/delegation-doctrine.md` states the claim-before-dispatch step, and `/autopilot` inherits it
  rather than restating it.
- A dry read of the doctrine by a fresh session produces a claim before its first builder dispatch.
- `python ci/run_all.py` green.

## Notes

`/mega-todos` has its own claim handling per its SKILL.md and is not the gap here; check it is
consistent with whatever the doctrine settles on, so the two do not diverge.
