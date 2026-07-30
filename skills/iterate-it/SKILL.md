---
name: iterate-it
description: Triggers on /iterate-it only. Converges a hypothesis through two phases (Explore, then Polish), one subagent per round, exiting once the score threshold is hit. Use when a one-shot /rate-it isn't enough and you want the panel to PROPOSE BETTER VERSIONS, not just judge.
argument-hint: "[--threshold=N] [--floor=N] [--explore-max=N] [--polish-max=N] [--research] <hypothesis>"
---

# /iterate-it

> Two-phase convergence. Explore until promising, then polish until shippable.

## When to use

- The dev has a non-obvious design decision (architecture, UX policy, refactor direction, prioritization) and wants an iterated answer.
- A solo or one-round /rate-it gave a verdict but no clear path forward.
- The dev wants subagents to PROPOSE BETTER VERSIONS, not just judge.

**Don't use** for code implementation tasks (subs can't write code well, just opinions), or when the dev already knows what they want (skip this, just implement it).

## Arguments

```
/iterate-it <hypothesis>
/iterate-it --threshold=7 --floor=9 --explore-max=6 --polish-max=3 [--research] <hypothesis>
```

- `<hypothesis>` — free-text. The initial proposal `P1` to evolve.
- `--threshold=<int>` — score that ends Explore phase. Default 7.
- `--floor=<int>` — score that ends Polish phase. Default 9.
- `--explore-max=<int>` — max Explore rounds. Default 6.
- `--polish-max=<int>` — max Polish rounds. Default 3.
- `--research` — main runs WebSearch before round 1 and passes findings into every sub. Off by default.

If dev passes a leading integer like `/iterate-it 3 <hypothesis>` (legacy N-arg form), TREAT IT AS A NO-OP and proceed with default phase counts. Mention briefly in the cost notice.

## Algorithm

Two phases. Each round = ONE subagent (not parallel — sequential, so each round sees prior rounds' verdicts).

### Phase A: Explore (up to `--explore-max` rounds)

Goal: find a proposal worth polishing.

Angle rotation per round (cycle if needed): skeptic → steelman → alternative-lens → shippability → misdiagnosis → skeptic. Pick the next angle that addresses the prior round's weakness. Don't repeat the prior round's angle unless deliberate.

Exit conditions (check after each round):
- **Promising**: sub score ≥ `--threshold` → enter Phase B with the just-evolved proposal.
- **Cap**: round count == `--explore-max` → enter Phase B with the best-scoring proposal so far (or stop if dev passed `--explore-max=0`).
- **Thrash**: 3 consecutive rounds with PIVOT or KILL markers → stop, report unconverged.

### Phase B: Polish (up to `--polish-max` rounds)

Goal: drive the promising proposal to `--floor`.

Angle bias: steelman (lock in strengths, expose remaining flaw) and shippability (produce ship-ready patch). Avoid alternative-lens / misdiagnosis (those belong in Explore — pivoting now wastes the convergence).

Exit conditions:
- **Floor hit**: sub score ≥ `--floor` AND main audit ≥ `--floor - 1` → done, report.
- **Cap**: round count == `--polish-max` → done, report whatever the best-scoring proposal is.
- **Backslide**: if a Polish round scores below `--threshold`, the polishing introduced a regression. Revert to prior proposal, count the round, continue.

### Per-round flow

For each round (regardless of phase):

1. **Write `P_R` clearly.** 1-3 short paragraphs. Mark explicit rejections (things prior rounds killed) so the sub doesn't re-propose them.

2. **Dispatch ONE sub** via Agent tool. Use the prompt template below. Pass `model: 'sonnet'`
   explicitly on the Agent tool call itself (the parameter, not just prompt text) - per global
   CLAUDE.md's subagent model rule, never rely on inheriting the session's model.

3. **Main audit.** After the sub returns, pick a score 1-10 yourself. Not a vote - a dissent signal vs the sub. If main deviates 1 point from sub, weight the synthesis toward the lower score. If main deviates ≥2, emit the MAIN DISSENT block in the final report.

4. **Synthesize `P_{R+1}`.** Read sub's evolution. Adopt the edit if it sharpens, reject if it bloats. The synthesized proposal must be SHORTER and SHARPER than `P_R`. Record marker (REVISION / PIVOT / KILL).

5. **Termination check** per phase rules above.

### Subagent prompt template

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

## Cost warning

Each round ≈ 25-50k tokens (depends on how much code-reading the sub does). Worst case 9 rounds × 50k ≈ 450k tokens. Typical 4-6 rounds total ≈ 150-250k.

Mention cost before round 1:

> "iterate-it: Explore up to 6 rounds + Polish up to 3 rounds, 1 sub each. ≈ 150-450k tokens total. Confirm or pass `--explore-max=N` / `--polish-max=N` to tighten."

Skip confirmation if dev passed explicit flags.

## Output (final report)

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

Do NOT call `AskUserQuestion` in the same turn as this report. Bundling a tool call with the report text makes the harness swallow the report - the dev ends up with a bare picker and no convergence summary (this has happened before, 2026-07-12). The report is the deliverable; it must always render as the turn's final message.

Close the report with a single plain-text line offering the next move, not a tool call:

> Ship it, run another manual round, or park it?

If the dev replies, act on it the following turn - that's when `AskUserQuestion` is safe to use (e.g. to pick which lift to apply next).

## Hard rules

- **ONE sub per round.** No parallelism. Sequential lets each sub see prior verdicts.
- **Always rotate angles in Explore.** Same angle twice in a row = groupthink risk.
- **Always main-audit each round.** It's the only check against sub sycophancy.
- **Never extend past `--explore-max + --polish-max`.** If the dev wants more, re-invoke with the final proposal as the new P1.
- **Cost transparency is non-negotiable.** Always estimate total tokens before round 1 unless dev opted out via explicit flags.
- **Don't let subs read this file.** They access /rate-it's flaw-hunt rules, not the orchestration. Keeps them focused.

## Example invocation

```
/iterate-it We should drop the lobby walking flow entirely - country picker has a PLAY button, decoration arena stays, done.
```

→ Estimates cost. Phase A: skeptic R1 (5/10), steelman R2 (6/10), alternative-lens R3 (8/10 → threshold hit, enter Polish). Phase B: steelman R4 (9/10 → floor hit). Report.

Worst case (no convergence): 6 explore + 3 polish rounds, report best-of with `unconverged` flag.

## Prior art

The pattern is taken from the 2026-05-18 Socka Heads stutter-debug session. The original 3×3 panel design (3 subs × 3 rounds) revealed that 9 sub-views converged to a single answer but cost ~270k tokens with redundant verdicts each round. The single-sub two-phase design produces the same convergence path more cheaply by letting each round see the prior verdict and rotating angles to attack remaining weaknesses, and gives the dev finer control (stop early at "good enough" 7, push for "shippable" 9).
