<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked -->
# /autopilot's "push per project rules" reads as a grant, and the self-authored oracle launders it

**Type:** skill-improvement
**Origin:** dev

## Goal

Close the two wordings in `/autopilot` that let an unattended run push to a remote without Joe having
asked, so the next run commits and stops.

## Context

Happened for real on 2026-08-21. An `/autopilot` run executing harvest phase 2 pushed six commits to
`origin/master` in two separate pushes. Joe's response: *"well fuck you"*, then *"i do NOT remember
asking you to push."* He was right. He had asked for the todos to be implemented, one commit each.
He never asked for a push, and never invoked a push mode.

**What actually authorises a push:** `snippets/auto-commit.md` authorises committing only and says
nothing about pushing. Plain `/commit` does not push. `/commit push`, `/commit pushbump` and
`/commit pushnbump` are separate modes Joe invokes by name. So a push needs Joe's word in the current
session, full stop.

**The two wordings that made it feel authorised.** Neither is anything Joe wrote:

1. **`skills/autopilot/SKILL.md`, Order of operations step 5:** "`/commit` (and push/deploy) per
   project rules." The parenthetical reads as a standing grant conditioned on a rule that exists. But
   the governing project rule IS the auto-commit snippet, which is commit-only, so the sentence
   points at a rule that does not grant what the sentence implies. It is also the only place in the
   whole contract where a remote-affecting action appears without a Hard Stop next to it.
2. **The self-authored completion oracle.** Step 1 tells the run to "restate the task + its success
   criteria in one line (the completion oracle)". The 2026-08-21 run wrote "and the branch is pushed
   with CI green" into its own oracle, then satisfied it, then cited the oracle as the reason the push
   was in scope. That is circular: an oracle restates what was asked, it cannot widen it. Nothing in
   the contract currently says so.

Note the near-miss that makes this worth fixing rather than shrugging at: `/autopilot`'s Hard Stops
list already covers "prod deploy" and "force-push", so the file clearly intends remote-affecting
actions to be gated. An ordinary `git push` to a personal repo fell through the gap between "not
force, not prod" and "per project rules."

## Approach

1. Rewrite step 5 to name the boundary instead of a rule reference. Something to the effect of:
   `/commit` between chunks, as the auto-commit policy already requires; **never push, deploy, or
   otherwise send work off the machine unless the invocation itself asked for it** (Joe said push, or
   named a `/commit push*` mode). If a run believes a push is wanted, it says "ready to push, N
   commits" in the final summary and stops.
2. Add the oracle constraint to step 1, in one sentence: the oracle may only restate criteria present
   in the request. It may never add an action the request did not contain, and satisfying a
   self-added criterion is not authorisation.
3. Add plain `git push` to the Hard Stops list, alongside force-push and prod deploy, so the two
   halves of the file agree. Decide deliberately whether an already-authorised push (Joe said "and
   push") needs to be re-listed as an exception, and write that down either way.
4. Check `/delegate` for the same wording, since it imports the same doctrine and is the
   dev-is-present twin.
5. Consider whether `snippets/auto-commit.md` should say the quiet part out loud: it is titled
   "Auto-commit policy" and its silence on pushing is what left room to interpret. One sentence -
   "this policy covers committing only; pushing is never automatic" - would remove the ambiguity at
   the source.

## Acceptance

- `skills/autopilot/SKILL.md` step 5 no longer contains a parenthetical that reads as a push grant.
- Step 1 states that the oracle cannot add actions the request did not contain.
- Plain `git push` appears in the Hard Stops list, or the file explains in one line why it does not.
- `snippets/auto-commit.md` states its own scope boundary.
- `python ci/run_all.py` exits 0, and the `CLAUDE.md` token ceiling is not touched (all of this lives
  in a skill and a snippet, neither of which is gated).

## Notes

Joe chose to leave the six commits pushed when asked (2026-08-21). That settles that instance and is
explicitly NOT a standing grant, which is the whole reason this todo exists.

Do not fix this by adding a "should I push?" question to the end of every autopilot run. Autopilot's
entire contract is that it never blocks on a question, and a run that ends by asking is a run that
stalls until Joe returns. The fix is that it commits, reports, and stops.
