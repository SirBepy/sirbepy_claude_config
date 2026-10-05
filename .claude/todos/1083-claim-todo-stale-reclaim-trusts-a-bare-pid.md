<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
# claim-todo.ps1's stale-claim reclaim trusts a bare PID, like reservations did

**Type:** task
**Origin:** ai

## Goal

A claim held by a dead session is reclaimable even when its PID has been recycled by an unrelated
live process, the same way id reservations now are.

## Context

Todo 988 (done, 21c4bdd) fixed `skills/close/reserve-todo-id.ps1`: markers now record the process
start time and liveness needs BOTH the pid alive AND a matching start time. The lane-C builder
confirmed on 2026-10-05 that `skills/close/claim-todo.ps1`'s stale-claim reclaim has the same
bare-pid shape (`Get-Process -Id <pid>` only) and left it unchanged because 988's Acceptance was
scoped to reservations. Claims self-release on completion, so exposure is lower, but an abandoned
claim whose pid is recycled never goes stale.

## Approach

Reuse 988's `procStartTicks` identity: write it into the claim file, and judge a two-signal claim
dead when the pid is gone OR the start time differs; keep mtime as the second signal per the
contract's staleness rule. Legacy claims without the field keep today's behaviour.

## Acceptance

- A test in `tools/test_close_claim_complete.py` with a claim whose pid is alive but whose start
  time differs is reclaimed once past the 4h mtime threshold.
- A genuinely live claim is never reclaimed.
- `skills/close/ai-todos-format.md`'s staleness paragraph matches the new rule.
