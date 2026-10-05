<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked 2026-10-05, complexity=HARD, worth=8, reconfirm-count=1, content-hash=4ca3112a -->
<!-- duplicate-checked: grepped this backlog for "ground check", "ground-check", "outbound-marker" and "hard stop" on 2026-09-24 - only 398 (Shortcut query-string plus-encoding), unrelated. -->
# The outbound ground check's done-state hard stop fires on the BE half of a BE/FE pair, where the FE work is demonstrably undone

**Type:** skill-improvement
**Origin:** ai

## Goal

`refs/outbound-ground-check.md`'s Verdict section stops hard-stopping a ticket whose only done-state
hit is the counterpart half of the same work, so the gate keeps the precision it claims to have.

## Context

Surfaced 2026-09-24 filing sc-55997 from a zng-app session. Filed here rather than in zng-app because
the fix edits this repo's `refs/outbound-ground-check.md`, per `CLAUDE.md`'s rule that a todo belongs
in the backlog of the repo it changes. The project session did not edit the ref.

`refs/outbound-ground-check.md`'s Verdict section (read 2026-09-24) lists as a HARD STOP:

> A tracker hit already in a **done-equivalent state**: Shortcut `Done` or `Testing`, Linear
> `state.type` of `completed`, `canceled`, or `started`.

Zirtue splits work across a BE ticket and an FE ticket routinely, and `skills/ticket/shortcut.md`
encodes that split itself (separate `BE:` and `FE:` title conventions, a Skill Set custom field with
Frontend/Backend values, and a `relates to` story link for "every BE/paired-FE counterpart"). So the
BE half reaching Complete BEFORE its FE half is filed is the normal sequence, not an anomaly.

**The live case.** Draft: `FE: Read loan limits from the loan configuration endpoint`. Query 2 hit
sc-55728 `BE: Loan Configuration Endpoint, Move Loan Limit to 5000`, workflow state `500018258`
(Complete), completed 2026-09-21 - a done-state hard stop by the letter of the rule. But query 3 came
back with the claim fully present at `origin/develop`: zero hits for `loans/configuration` under
zng-app's `lib/`, and all five limits still literal at `loan_constants.dart:293-305`. The FE work had
provably not been done by anyone. The hard stop was a false positive, and it was overridden by hand.

That matters because the section states its own design intent right above the list:

> They are high precision on purpose: a gate that fires on maybes trains the dev to click through,
> which turns "stopped" back into "informed".

A stop that fires on every FE ticket filed after its BE counterpart ships is exactly the click-through
training the paragraph warns about.

**Second live case, 2026-09-29, and it falsifies step 2 below.** Filing sc-56121
`BE: Optimize entity logo images on upload` from a zng-admin session. The stop that fired was the
**merged-PR** clause, not the done-state one: `gh pr list -R zirtue-corp/zng-api --state merged
--search "image"` returned PR #833 "[ZNG] Entity Image Upload Flow Refactor", merged 2026-09-22,
which touches the exact file the claim named
(`libs/shared/src/service/entity-image-storage.service.ts`). Query 3 then disproved it outright:
`git show origin/develop:libs/shared/src/service/entity-image-storage.service.ts` still reads
`writeBlob(..., file.buffer, ...)`, a straight passthrough with no resizing, and
`git grep -iE "sharp|jimp|resize\("` over `origin/develop` returns zero hits, so no image library
exists in the repo to have done it. The PR was a refactor that CREATED the service; it never added
the behaviour. Overridden by hand on the dev's explicit "File it" after the false positive was
shown to him.

So the merged-PR clause has the same failure mode as the done-state clause, for the same reason:
"a commit touched this file" and "the behaviour exists" are different claims, and a refactor,
rename, or extraction satisfies the first while leaving the second false. Step 2 below was written
before this case and should be reversed, not kept.

## Approach

Query 3 is already the discriminator and already runs, so no new query is needed - only the verdict
logic has to consult it.

1. In the Verdict section, qualify the done-state hard stop: it stands when query 3 finds the claim
   ABSENT at the tracked branch (the work really is done). When query 3 finds the claim PRESENT, the
   done ticket covered a different half or a different era of the work, and the verdict drops to
   REUSE CANDIDATE - surface the hit to the dev with its id, state and completion date, and let him
   decide, rather than blocking the write.
2. ~~Keep the merged-PR hard stop as-is. A merged PR touching the claim's own file is different
   evidence and does not have this failure mode.~~ **Revised 2026-09-29, see the second live case
   above:** it does have the failure mode. Apply the same query-3 qualifier to it. A merged PR
   touching the claimed file hard-stops only when query 3 finds the claim ABSENT; when the claim is
   still present at the tracked branch, the PR touched the file without adding the behaviour, so the
   verdict drops to REUSE CANDIDATE and names the PR number and merge date for the dev.
3. State the rule generically (claim present at the tracked branch), not as a BE/FE special case. The
   same shape occurs for a design-typed `UX:` ticket marked Done whose implementation ticket has not
   been filed, and the existing REUSE CANDIDATE paragraph already treats design-typed hits as live
   reuse targets rather than blockers.
4. No hook change. The four guards consume a marker and never read the verdict text, so this is a
   prose fix to the one file; confirm that by grepping `hooks/` for any done-state logic before
   assuming it.

## Acceptance

- `refs/outbound-ground-check.md` no longer hard-stops a done-state tracker hit when query 3 finds
  the claim present at the tracked branch, and says why in one sentence.
- The same qualifier covers the merged-PR hard stop, with the refactor-touched-the-file case named
  as the reason (per the 2026-09-29 sc-56121 case in Context).
- A grep of `hooks/` confirms no guard duplicates the done-state rule in code.
- `python ci/run_all.py` passes after the edit.
