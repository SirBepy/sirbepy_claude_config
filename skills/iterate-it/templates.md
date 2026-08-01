# /iterate-it templates

> Read this once, at round 1. Both templates below are reused verbatim across every round -
> only the bracketed placeholders change.

## Subagent prompt template

```
You are the subagent for /iterate-it round <R>, phase <Explore|Polish>. Read ~/.claude/skills/rate-it/SKILL.md and apply the Flaw hunt, Role, Anti-sycophancy rules.

HARD CONSTRAINTS:
- Do NOT spawn further subagents.
- Do NOT call AskUserQuestion.
- Return only the rating block + EVOLVED PROPOSAL section. Be terse.

HYPOTHESIS (P_R):
<full text of current proposal>

<CONTEXT (--research findings, prior-round rejections, prior scores)>

WHAT I WANT:
1. Score 1-10.
2. Highest-risk assumption.
3. EVOLVED PROPOSAL section labeled "P_{R+1}" with concrete edits and one marker:
   - REVISION: small edits to the current proposal
   - PIVOT: different approach, same problem
   - KILL: abandon the problem framing entirely

ANGLE FOR YOU: <skeptic | steelman | alternative-lens | shippability | misdiagnosis>
<one-paragraph angle-specific brief>
```

## Final report template

```
# /iterate-it converged in <R> rounds (<explore-rounds> explore + <polish-rounds> polish)

**Final proposal (P_<R+1>):**
<synthesized final>

**Score trajectory:** P1=<s1> → P2=<s2> → ... (sub scores)
**Main audit trajectory:** P1=<a1> → P2=<a2> → ...
**Phase transition:** entered Polish at round <X> with score <Y>
**Termination reason:** <floor hit | cap hit | thrash | unconverged>

**Evolution log:**
- P1 → P2: <one-line summary>
- P2 → P3: ...

**Explicit rejections (never re-propose):**
- <thing killed in round X>

[If main audit deviates ≥ 2 from sub:]
**MAIN DISSENT:** main scored <X>, sub <Y>. <one-paragraph why>. Take this verdict with the dissent in mind.
```
