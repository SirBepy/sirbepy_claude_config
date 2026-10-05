<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- duplicate-checked: grepped this backlog and done/ for "visual", "screenshot", "Phase 0" and "close". 459 (id mismatch) and 324 (screenshot deletion moved to /disk-doctor) both concern the screenshot FOLDER, not the check that reads it. Nothing covers the flag being satisfied by the wrong kind of capture. -->
# /close Phase 0's visual-work check is satisfied by automated screenshots

**Type:** skill-improvement
**Origin:** ai

## Goal

`/close`'s visual-work check fires when a session shipped a user-facing visual change that Joe never
saw, and does NOT get silenced by a test suite that happened to write PNGs.

## Context

Found 2026-09-26 running `/close` on the `claude_usage_in_taskbar` repo after a `/loop-todos` session
that shipped a real 5px layout fix plus several CSS relocations.

`skills/close/SKILL.md` Phase 0 says:

> **Visual-work check.** If any file changed this session matches `.css`/`.scss`/`.less`, or is
> otherwise a user-facing visual/layout change, and the zero-screenshots flag above is true, add
> "show Joe a live screenshot of the visual change" to the unfinished-commitments list below.

Both halves of that condition were met in spirit: ten `.css` files changed, and Joe was shown nothing.
But **the zero-screenshots flag read FALSE**, because `pnpm run test:view` had written **29** PNGs
into this session's own `.for_bepy/screenshots/<id>/` folder during the verification runs. The check
therefore did not fire, and the item was only filed because the session noticed by hand and
overrode it.

The flag is doing what it says - Phase 0 defines it as "whether this session captured any screenshots
at all" - but that is not the question the rule is for. The rule exists because a green headless pass
cannot detect "this looks wrong" (its own cited incident, 2026-08-01, is an AUQ card-height CSS fix
that shipped on a passing Playwright test alone). An automated harness capture is a *stronger* case of
exactly that failure mode, not evidence against it: nobody looked at those 29 files either.

Any session that runs `/e2e` or `pnpm run test:view` in a repo whose specs write `@shot` frames will
silence this check for free, which is most verification-conscious sessions. The more thorough the
session, the more reliably the guard disarms.

## Approach

1. **Re-read Phase 0 and Phase 3 step 3 together before changing either.** They share the flag and
   the folder id, and Phase 3's `mismatch` branch already depends on the current semantics - a naive
   redefinition breaks that counter. Note that Phase 3's screenshot COUNT genuinely does want every
   PNG, so the two uses need separating rather than one being redefined.
2. The distinction to encode is *who the capture was for*, not whether one exists. Candidates,
   cheapest first:
   - Key the check on whether anything was **shown** to Joe this session - a `show-shot.ps1` /
     `/preview` / `SendUserFile` call in the transcript - rather than on files existing on disk. This
     matches the rule's actual wording ("show Joe"), needs no new bookkeeping, and is greppable.
   - Or have the check ignore PNGs written by a test runner, distinguished by the spec-driven naming
     the harness already uses. Weaker: it is a naming convention, not a guarantee.
3. Whichever is chosen, state it in Phase 0 explicitly, including that an automated capture does not
   count. The current wording is not wrong so much as silent on the case, which is why it read as
   satisfied.
4. Check whether `/e2e` and `/screenshot` need a matching note, since they are the skills that write
   the frames that trip it.

## Acceptance

- A session that changes CSS, runs a screenshot-writing suite, and shows Joe nothing still gets the
  visual-work item added in Phase 0.
- A session that genuinely did show Joe a frame does NOT get it added.
- Phase 3 step 3's counter and its `mismatch` branch still behave as documented, verified by reading
  both paths against the new semantics rather than assumed.
- `python ci/run_all.py` passes (skill-frontmatter validation plus the always-loaded instruction token
  budget).

## Notes

- Do not fix this by deleting the flag and always adding the item. A session that already showed Joe
  the change would then get a false chore every time, and the rule would start being ignored - which
  is worse than the current gap.
- The `claude_usage_in_taskbar` instance of the missed item was filed as that repo's todo 980 on
  2026-09-26, so the concrete case is not lost while this is open.
