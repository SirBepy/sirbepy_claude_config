---
name: iterate-it
description: Converges a hypothesis through two phases (Explore, then Polish), one subagent per round, exiting once the score threshold is hit. Use when a one-shot /rate-it isn't enough and you want the panel to PROPOSE BETTER VERSIONS, not just judge. Also invoked as a bounded nested step by /autopilot and /auto-do-todos.
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

## Algorithm

Two phases. Each round = ONE subagent (not parallel — sequential, so each round sees prior rounds' verdicts).

### Phase A: Explore (up to `--explore-max` rounds)

Goal: find a proposal worth polishing.

Angle rotation per round (cycle if needed): skeptic → steelman → alternative-lens → shippability → misdiagnosis → skeptic. Pick the next angle that addresses the prior round's weakness. Don't repeat the prior round's angle unless deliberate.

Exit conditions (check after each round):
- **Promising**: sub score ≥ `--threshold` AND main audit ≥ `--threshold - 1` → enter Phase B with the just-evolved proposal.
- **Cap**: round count == `--explore-max` → enter Phase B with the best-scoring proposal so far (or stop if dev passed `--explore-max=0`).
- **Thrash**: 3 consecutive rounds with PIVOT or KILL markers → stop, report unconverged.

### Phase B: Polish (up to `--polish-max` rounds)

Goal: drive the promising proposal to `--floor`.

Angle bias: steelman (lock in strengths, expose remaining flaw) and shippability (produce ship-ready patch). Avoid alternative-lens / misdiagnosis (those belong in Explore — pivoting now wastes the convergence).

Exit conditions:
- **Floor hit**: sub score ≥ `--floor` AND main audit ≥ `--floor - 1` → done, report.
- **Cap**: round count == `--polish-max` → done, report whatever the best-scoring proposal is.
- **Backslide**: if a Polish round scores below `--threshold`, the polishing introduced a regression. Revert to prior proposal, count the round, continue.

### Progress checklist

In an attended Conductor run (`write_plan` exists and no caller owns the checklist - see Output),
declare the whole checklist before round 1, one row per possible round up to the caps: `Explore
round 1` ... `Explore round <explore-max>`, then `Polish round 1` ... `Polish round <polish-max>`,
all `pending`. Joe wants to see the remaining budget ahead, not rows appearing one at a time.

- Mark the current round `active` before dispatching its sub.
- After the main audit, mark it `done` with a one-line `detail`:
  `<angle> · <score>/10 (audit <a>) · <MARKER>: <what changed>` (append `, reverted` on a Backslide).
- On exit, mark every unreached row `skipped` in the same call that completes the last round - an
  early Explore exit skips the rest of Explore, a floor hit skips the rest of Polish.

The checklist is progress only. The final verdict never lives in it - that is the report card.

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

The exact prompt to send each sub lives in `templates.md`, next to this file. Read it once, at
round 1 - every subsequent round reuses the same template with `<R>`, `<phase>`, and the
hypothesis text swapped in.

## Cost

Each round ≈ 25-50k tokens; typical 4-6 rounds ≈ 150-250k, worst case 9 rounds ≈ 450k. No
up-front estimate or confirmation - Joe dropped it 2026-09-29. Start round 1 directly. Sum each
sub's reported token usage as the run goes; it lands in the report card's Run stats.

## Output (final report)

Three shapes, picked by where the run is:

- **Attended Conductor run** (`show_preview` exists, no caller skill owns the turn): the report card
  below. This is the default whenever Joe invoked `/iterate-it` himself in Conductor.
- **Unattended** (see below) or **nested inside another skill with its own checklist**: the text
  report in `templates.md`, and no `write_plan` calls - each call replaces the whole checklist, so
  iterate-it would wipe the caller's.
- **No Conductor** (plain CLI, no `show_preview`): the text report in `templates.md`.

### The report card

**Rendered by a script, not hand-written HTML.** `skills/iterate-it/scripts/render_report.cjs`
always produces the same layout from a run JSON file. Its header comment holds the exact JSON shape.
What is open and what is collapsed is fixed in the script, per Joe (2026-09-29): open are the score,
the one-line answer, `Ended: <phase> round <n>` with its reason, the final solution bullets, and the
MAIN DISSENT banner when main audit and sub differ by ≥2. Collapsed are the score chart, round by
round, biggest remaining risk, rejected ideas, and run stats. Promoting a collapsed item to open
is an edit to the script, not a per-run call.

1. Write the run JSON with the Write tool to `C:\tmp\iterate-it\<topic-slug>.json`.
   `ended.round` counts within its phase, matching the checklist rows. Include every round's
   highest-risk assumption and synthesized proposal; nothing from the run is dropped, it is only
   collapsed.
2. `node C:\Users\tecno\.claude\skills\iterate-it\scripts\render_report.cjs --run <json> --out <same path>.html`
3. Read the HTML back and push it with `show_preview`: slug `iterate-it-<topic-slug>` (per-topic, so
   two runs in one chat don't replace each other's card), title `iterate-it: <topic>`.
4. Send one short bubble: `<score>/10 - <answer>`, the MAIN DISSENT line if there is one, then the
   next-move line below. The card lands inline in the chat, so don't restate its contents.

**Attended session (a dev is present to read it).** Do NOT call `AskUserQuestion` in the same turn as
this report. Bundling a tool call with the report text makes the harness swallow the report - the dev
ends up with a bare picker and no convergence summary (this has happened before, 2026-07-12). The
report must render as the turn's final message: the point is that the dev actually reads the
converged decision before anything else lands on top of it, not merely that some hosts happen to
swallow the preceding text - a Conductor session delivers the report through its own `send_message`
bubble, which a question card cannot swallow, but the same-turn continuation still denies the dev the
beat to react before more work ships, so the rule holds there too, for the attention reason rather
than the rendering one.

This holds even when the dev already pre-authorized next steps ("go ahead and implement it"). That authorization changes what happens on the FOLLOWING turn, never whether a tool call chains onto this one - continuing straight into `Read`/`Edit`/implementation calls in the same turn as the report is the exact failure this rule guards against (sc-54844, 2026-08-11: the report rendered fine, but the turn then continued straight into implementation tool calls anyway).

**Unattended invocation (no dev in the loop - e.g. `/autopilot`'s bounded iterate-it step).** The
final-message rule does NOT apply here, and must not be applied here: there is no dev to read a
stopped turn, so ending the turn on the report would stall the caller's run with nobody left to send
the next message, not protect anyone's attention. `/autopilot`'s own "Nested-question suppression
contract" already governs this exact case (always ship on cap/floor, per its section 5) - return the
report with the ship/floor decision and let the caller's turn continue past it in the same turn to
act on that decision. An invocation counts as unattended exactly when the invoking context carries
its own documented auto-decision contract (autopilot's suppression rules are the only one today);
absent that, default to the attended behavior above.

In the attended case, the next move is a single plain-text line, not a tool call. It ends the card
run's bubble. In the text report it closes the SUMMARY block, and detail follows below the rule:

> Ship it, run another manual round, or park it?

If the dev replies, act on it the following turn - that's when `AskUserQuestion` is safe to use (e.g. to pick which lift to apply next). In the unattended case, skip this line entirely: the caller's own contract already states the next move, and the report's job is to hand the decision back inline, never to prompt anyone.

## Hard rules

- **ONE sub per round.** No parallelism. Sequential lets each sub see prior verdicts.
- **Always rotate angles in Explore.** Same angle twice in a row = groupthink risk.
- **Always main-audit each round.** It's the only check against sub sycophancy.
- **Never extend past `--explore-max + --polish-max`.** If the dev wants more, re-invoke with the final proposal as the new P1.
- **Don't let subs read this file.** They access /rate-it's flaw-hunt rules, not the orchestration. Keeps them focused.

## Example invocation

`/iterate-it <hypothesis>` runs Explore then Polish rounds per the algorithm above, and reports convergence (or `unconverged` if the round caps are hit first).
