# /rate-it panel mode

> Read this only when an integer N was passed to `/rate-it`. Solo ratings never need this file.

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

Spawn N Agent calls in parallel (`general-purpose` subagent_type). Each gets this prompt, with
that subagent's assigned lens swapped in:

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
> - Return only the rating block (verdict + reasoning + How to raise).

## Synthesis (main agent runs LAST)

Order matters: main rates AFTER reading subagent outputs. Main rating first contaminates the
merge with anchor bias.

1. Wait for all N subagent results.
2. Run own flaw hunt + own rating, informed by subagent flaws but not bound to their score.
3. Final score = median of all (N + 1) scores. Ties round down (harsher).
4. Flaws = union of all flaws found across subagents + main; dedupe near-duplicates, keep the
   sharpest phrasing.
5. How-to-raise = best 2-3 lifts across all outputs, ordered ascending by unlocked score.
6. Surface dissent: if any individual score deviates ≥2 points from the final median, append one
   line: `Dissent: 1 rater scored X/10 - [one-line reason]`.
