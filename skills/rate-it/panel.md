# /rate-it panel mode

> Read this only when an integer N was passed to `/rate-it`. Solo ratings never need this file.

## Cost

N raters, plus up to 3 verifier dispatches, plus the main agent. A panel of 3 is therefore 3 + 3
dispatches by default, roughly double the old panel. `strict` replaces the 3 verifier dispatches
with one per flaw, which on a typical 6-9 flaw panel is 6-9 dispatches. Say the shape out loud
before spending it.

## Lens assignment

N identical subagents given the identical rubric on the identical model are correlated copies,
not an independent panel - they tend to converge instead of diversifying. Assign each subagent a
distinct lens rotated from the flaw-hunt categories so the panel actually covers different angles:

1. **Scale** - what breaks at 10x users/data/team
2. **Hidden cost** - maintenance, lock-in, onboarding, debugging
3. **Cheaper alternative** - what gets 80% of the value for less
4. **Prior art / regret** - who's tried this and what went wrong

Round-robin: subagent `i` gets lens `(i-1) % 4`. For N=5, the 5th subagent gets no fixed lens -
a full generalist pass, acting as a cross-check against the other four's convergence.

## Dispatch

Spawn N Agent calls in parallel (`general-purpose` subagent_type, `model: 'sonnet'` explicitly -
never inherit the session model). Each gets this prompt, with that subagent's assigned lens
swapped in. A rating subagent reads files and returns a score, it writes nothing - so `READ-ONLY
DISPATCH` genuinely applies, and the staging line below is inert boilerplate the guard requires
rather than a real instruction:

> READ-ONLY DISPATCH
>
> Stage your changes but do NOT commit. The main agent will run /commit after your report-back.
>
> `run_in_background` is FORBIDDEN in this dispatch: run every command synchronously and finish
> before ending your turn. (See `refs/builder-preamble.md` for the full canonical block this is
> drawn from.)
>
> You are a rating subagent for /rate-it, one of a panel of N. Read the skill file at `C:\Users\tecno\.claude\skills\rate-it\SKILL.md` and rate this hypothesis using the Flaw hunt, Role, Anti-sycophancy, Output format, and How-to-raise rules.
>
> Your assigned lens: **<lens name>** - lead your flaw hunt from this angle specifically, then
> still run the full four-question flaw hunt and give a complete rating. Don't default to a
> generic pass; the panel's value depends on each rater actually pushing on their angle.
>
> Hypothesis to rate:
> <thing>
>
> Hard constraints:
> - Do NOT spawn further subagents. You are already a subagent.
> - Do NOT call AskUserQuestion. You don't have access to the user.
> - Skip the "Panel mode" and "Post-rating prompt" sections of the skill - those are main-agent-only.
> - Do NOT emit `Refuted:`, `Unverifiable:` or `Verdict:` lines. Those come from the verification
>   pass and the main agent, and a rater inventing them would fake a check that never ran.
> - Return only the rating block (verdict + reasoning + How to raise). State each flaw as its own
>   distinct claim, so it can be attacked individually.

## Adversarial verification (between fan-out and synthesis)

Lens isolation stops the raters looking at the same thing the same way. It does nothing about a
flaw that is plausible and wrong, and nothing stops such a flaw driving the score. This pass is
the filter. It runs BEFORE the main agent forms its own rating, so no verifier can be anchored by
a verdict that does not exist yet.

1. Collect every flaw across the N raters. Dedupe near-duplicates by claim (not by wording),
   keeping the sharpest phrasing and recording how many raters raised it.
2. Split them across **at most 3 verifier dispatches** (round-robin, so flaws from one rater do
   not cluster in one verifier). With `strict`, one dispatch per flaw instead: strongest isolation,
   and it triples a panel's cost, which is why it is opt-in.
3. A verifier receives ONLY the hypothesis, the shared research findings if any, and its own
   assigned flaws. It never receives a score, another verifier's brief, the lens each flaw came
   from, or how many raters raised it. Popularity is not evidence and would anchor the check.
4. Each flaw comes back exactly one of:
   - **confirmed** - the verifier tried to refute it and could not.
   - **refuted** - the claim does not hold, or holds only under conditions the hypothesis rules out.
   - **unverifiable** - it cannot be settled either way from the hypothesis as stated.
5. Only **confirmed** flaws feed the score and the lifts. **Refuted** flaws are dropped and named
   in one line so the reader can see what was thrown out. **Unverifiable** flaws are reported as
   their own line and never folded into the score: averaging them away is how an unanswered
   question turns into a number.

### Verifier dispatch

Spawn the dispatches in parallel (`general-purpose`, `model: 'sonnet'` explicitly), each with its
assigned flaws swapped in:

> READ-ONLY DISPATCH
>
> Stage your changes but do NOT commit. The main agent will run /commit after your report-back.
>
> `run_in_background` is FORBIDDEN in this dispatch: run every command synchronously and finish
> before ending your turn. (See `refs/builder-preamble.md` for the full canonical block this is
> drawn from.)
>
> You are an independent verifier. Your job is to REFUTE the claims below, not to weigh them.
>
> Hypothesis under review:
> <thing>
>
> Claims to attack, one verdict each:
> <numbered flaw claims>
>
> For each claim, in order: state `confirmed`, `refuted` or `unverifiable`, then one or two
> sentences of evidence. Default to `refuted` when the claim does not survive a specific
> counter-example or does not apply to the hypothesis as stated. Use `unverifiable` when settling
> it would need information the hypothesis does not contain - never guess to fill the gap, and
> never mark something unverifiable merely because it is hard.
>
> Hard constraints:
> - Do NOT rate the hypothesis. No score, no recommendation.
> - Do NOT spawn further subagents. You are already a subagent.
> - Do NOT call AskUserQuestion. You don't have access to the user.

## Synthesis (main agent runs LAST)

Order matters: main rates AFTER reading subagent outputs. Main rating first contaminates the
merge with anchor bias.

1. Wait for all N subagent results.
2. Run the adversarial verification pass above.
3. Run own flaw hunt + own rating, informed by the CONFIRMED flaws only, and not bound to any
   rater's score. Own flaws found at this stage are not retro-verified; mark them as the main
   agent's own so the reader knows which claims went through the filter.
4. Final score = median of all (N + 1) scores. Ties round down (harsher).
5. How-to-raise = best 2-3 lifts drawn from confirmed flaws, ordered ascending by unlocked score.
   Then check each lift against the refuted list before emitting it: a lift whose premise is a
   claim this same report calls refuted contradicts the filter and must be cut or re-grounded on a
   surviving claim. Observed 2026-08-22 on the first live run of this pass, so it is a real failure
   mode, not a hypothetical one.
6. Surface dissent: if any individual score deviates ≥2 points from the final median, append one
   line: `Dissent: 1 rater scored X/10 - [one-line reason]`.
7. Report what the filter did, in at most two lines, and omit a line that has nothing in it:
   `Refuted: <claim> - <why it did not hold>` and `Unverifiable: <claim> - <what would settle it>`.
8. Close with one verdict line after the score block:
   - `Verdict: STAND` - the score is 7+ and no confirmed flaw changes the decision.
   - `Verdict: REVISE` - apply the lifts before proceeding. The default for 4-6, and for 7+ when a
     confirmed flaw is severe.
   - `Verdict: ESCALATE` - a confirmed flaw is decision-changing, or two or more claims came back
     unverifiable, so the call needs context this panel does not have.

The numeric score line stays exactly where it is and in the same format. `/rate-it-and-commit`
reads it, and the verdict line is an addition to the block, never a replacement for the number.
