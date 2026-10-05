<!-- Claim before executing: .claude/todos/.claims/984-pay-down-the-28-skill-descriptions-grandfathered-past-the-budget.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=7, reconfirm-count=1, content-hash=e5bc0cb5 -->
<!-- duplicate-checked -->
<!-- checked against 976 (done/, shipped 2026-09-11). 976 added the gate and trimmed the one
     in-scope offender; it deliberately grandfathered everything else so the new gate would not
     break unrelated commits on day one. This todo is that grandfathered set, which 976 explicitly
     called closed debt needing its own trim-or-exempt decision per skill. Different work. -->
# Twenty-eight skill descriptions are grandfathered past the budget they now have

**Type:** task
**Origin:** ai

## Goal

Empty `LEGACY_OVER_BUDGET_DEBT` in `ci/check_skill_frontmatter.py`, one skill at a time, until the
description budget applies to every model-invocable skill without exception.

## Context

Todo 976 shipped the budget gate (25 words / 120 chars, enforced as a hard FAIL) on 2026-09-11, and
grandfathered every description already over it so the gate would not break every unrelated session's
commit the day it landed. That grandfathered set is the work here.

Why it is worth paying down rather than leaving: a skill's `description` loads into the system prompt
for **every session in every project**, not only when the skill runs. It is a per-session tax on work
that has nothing to do with the skill. The gate stops the number growing; it does not shrink it.

The two worst by a wide margin, measured 2026-09-11:

- `impeccable` at roughly 895 characters, which is over seven times the budget on its own.
- `generate` at roughly 489 characters.

Those two alone are most of the remaining cost. Start there and the rest is small.

**A correction already applied, so it is not re-litigated.** 976 originally shipped TWO exemption
sets: this debt set, plus a `CHAIN_CALLEE_EXEMPT` set holding 16 skills that a parent flow invokes,
on the theory that a chain callee's description does no routing work. That theory was wrong and the
two sets were merged the same day. Every one of those 16 was still model-invocable, so its
description sits in the fleet-wide listing and costs every session like any other. The exemption's
own rationale contained the contradiction: those skills cannot carry `disable-model-invocation: true`
precisely BECAUSE a caller needs to find them in the listing. Being called by a parent and being
routed on your own description are not mutually exclusive. Do not reintroduce that distinction.

The one sound automatic exemption is `disable-model-invocation: true`, already applied live from the
file. A skill that never enters the listing genuinely costs nothing.

## Approach

1. Re-measure first. The set is dated and skills change; work from fresh numbers, not the two cited
   above.
2. Take `impeccable` and `generate` first, separately from the rest. They are the bulk of the cost
   and each probably deserves its own thinking rather than a batch pass.
3. Per skill, the decision is trim, or carry `disable-model-invocation: true` if it is genuinely
   slash-only, or stay in the set with a stated reason. A skill whose description genuinely cannot
   reach budget without losing routing is a legitimate permanent entry, but it must say why in its
   trailing comment.
4. **For every trim, name what the skill must still be found by before editing**, and check the
   trimmed text still contains it. A description trimmed until it stops routing is worse than one
   over budget, and that failure is silent: nothing tests that a skill is still discoverable.
5. Remove each paid-down name from the set as you go, so the set is always the true remaining debt.

## Acceptance

- `impeccable` and `generate` are both resolved, by trim or by a stated permanent exemption.
- Every skill removed from the set has its retained trigger terms named in the commit or the todo.
- No skill is moved out of the set by widening the budget or by reviving a chain-callee style
  exemption.
- `python ci/run_all.py` passes, with the gate still enforcing as a FAIL.

## Notes

- The gate was mutation-tested when it shipped: bloating a compliant skill's description produced
  exit 1 with an actionable message, and restoring it produced exit 0. It is not vacuous.
- Do not batch all 28 into one dispatch. Each trim is a judgement about what the skill must remain
  findable by, and a builder given 28 at once will optimise for the character count.
