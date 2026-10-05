# Degraded finish review

Used two ways: as the prompt handed to a fresh `general-purpose` subagent when
the harness has a subagent tool but no agent type registered under the name
`impeccable-finish-reviewer` (Claude Code's Agent tool: types are `claude`,
`Explore`, `general-purpose`, `Plan`, `statusline-setup` - none of them this
skill's named agents), or followed in-thread, after stepping fully out of the
build context, on a harness with no subagent tool at all.

## Inputs

The caller passes all of these; this file has no browser and no memory of the
build, so anything not handed over cannot be checked:

- the original request and the confirmed answers from Setup
- the artifact path
- desktop and mobile screenshot paths
- the direction contract
- existing hook findings for the file(s) touched
- the QUALITY BAR card and approved comp paths (when a comp was approved)
- the craft-floor reference path ([craft-floor.md](../craft-floor.md))

Never claim to have inspected a viewport, a comp region, or a hook finding
that was not actually handed in as a path or a pasted value.

## Review

1. **Comp fidelity.** When an approved comp was supplied, compare it against
   the screenshots region by region (hero, then each section), not as one
   full-page thumbnail. Name the comp region alongside each gap: wrong
   lettering, flattened material, crude controls, a reordered section that
   reads similar but is not.
2. **Craft-floor compliance.** Check the screenshots against
   [craft-floor.md](../craft-floor.md)'s verify list (contrast, spacing, type
   floors). A floor violation is material, not a nit.
3. **Hook findings triage.** For each existing finding passed in, mark it
   fixed, still-open, or not-applicable (the screenshots cannot confirm it
   either way).
4. **Material findings.** New issues visible in the screenshots that the
   hook would not catch: layout, pacing, motion-as-material, copy fit.
5. **Disposition.** One of `PASS`, `NEEDS-WORK`, or `REBUILD`, with the
   deciding reason in one line. `REBUILD` means fidelity failed wholesale,
   not in patches - the caller stops the fix batch and takes it to the user
   rather than patching toward a comp the build never matched structurally.

Return exactly these five sections, in this order, even when a section has
nothing to report (say so explicitly rather than omitting it) - the caller
verifies the return carries all five before acting on it.

## Verdict pass (second round, after a fix batch)

Re-score only the findings this review already flagged, each
`resolved` / `partial` / `unresolved`. Do not open a new hunt; new findings on
a recapture are the first round's miss, not grounds for a third round. Two
rounds is the ceiling for an unattended run.

## Degraded disclosure

This substitution (general-purpose agent or in-thread pass, either one) gets
one line in the caller's final report, in the shape
`⚠️ DEGRADED: finish-review ran via <general-purpose agent|in-thread pass> (no impeccable-finish-reviewer agent type on this harness)` -
never silent, matching the convention in [critique.md](../critique.md).
