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

Two blocks, in this order. The dev reads the first and stops; everything he might want
later goes below the rule. Never open with round counts or phase names - that is process
metadata, not the answer, and burying the score under it is the exact failure this shape
fixes.

```
<emoji> <score>/10 - <the answer in one line, naming what won>

<2-4 bullets, the final proposal only. What it is and what it does, not how it evolved.>

Ship it, run another manual round, or park it?

---

**Detail** (<R> rounds: <explore-rounds> explore + <polish-rounds> polish, <termination reason>)

Scores: <s1> → <s2> → ... (main audit: <a1> → <a2> → ...), entered Polish at round <X>

- P1 → P2: <one-line summary of what changed and why>
- P2 → P3: ...

Rejected, never re-propose: <thing killed in round X>; <thing killed in round Y>

[If main audit deviates ≥ 2 from sub:]
**MAIN DISSENT:** main scored <X>, sub <Y>. <one paragraph why>. Weigh the verdict accordingly.
```

Rules for the summary block:

- Score emoji and number are the first characters of the report. No heading above them.
- The bullets state the final design, not its history. If a bullet only makes sense once you
  know what round 3 killed, it belongs below the rule.
- The next-move line closes the SUMMARY, not the whole report. Detail follows it.
