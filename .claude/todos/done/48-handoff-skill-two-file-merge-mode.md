<!-- Claim before executing: .claude/todos/.claims/ per close/ai-todos-format.md -->
<!-- cleanup: last-checked never, complexity=unknown (shallow pass), reconfirm-count=1, content-hash=- -->
# /handoff: support a two-file mode for multi-session merges

**Type:** skill-improvement
**Origin:** ai

## Goal

`/handoff` (and `/create-todo`'s bare handoff mode) always produce exactly one artifact per
`ai-todos-format.md`'s Handoff mode section. On zng-app (2026-08-08), Joe asked for a
deliberate deviation: a short default handoff todo (normal shape, stays PLAN.md-mergeable)
that links to a separate, much longer "bigass" companion file carrying the full narrative â€”
specifically because he was merging this session's handoff with a concurrent session's, and
wanted the top-line PLAN.md pointer to stay simple while the deep detail lived elsewhere.

## Context

Ad-hoc satisfied this turn by hand: wrote todo 111 (short, standard sections, Context/Notes
pointing at todo 112) and todo 112 (full narrative, same template, cross-linked back). Worked,
but nothing in the skill documents this as a supported mode, so it's undiscoverable and every
future "I'm merging multiple sessions" request re-derives the same shape from scratch.

`ai-todos-format.md`'s Handoff mode section (`~/.claude/skills/close/ai-todos-format.md`) is
the single source of truth both `/handoff` and `/create-todo`'s bare mode read from - this is
where the two-file variant belongs, not a per-command special case.

## Approach

Add a "two-file / merge mode" subsection to Handoff mode, triggered by an explicit ask (not a
default - default stays single-file). Shape: file N = the normal template, Context section
opens with a pointer sentence to file N+1; file N+1 = same template, unbounded length, Notes
section says which N it's a companion to. Both still get one PLAN.md line each? Or just N -
worth deciding: this session only pinned N (111) to PLAN.md and left N+1 (112) as a pure
Context-section pointer, not its own PLAN.md line. That read as the more mergeable choice and
is probably the right default for the new subsection.

## Acceptance

- `/handoff --split` (or similar explicit flag/phrasing) produces exactly this two-file shape
  without re-deriving it from a bare description each time.
- Bare `/handoff` (no split request) is unchanged - still single-file.

## Notes

- Re-verified 2026-08-08: premise still holds.

- **Validated plan (2026-08-08).** Premise re-verified against the tree this date and it holds.
  Concrete plan: add a two-file merge-mode subsection to `close/ai-todos-format.md`'s Handoff mode,
  triggered by an explicit split request - file N is the normal template with a Context pointer to
  N+1, file N+1 is the same template, and only N gets a PLAN.md line. This is the reading the todo
  itself already states. This was produced by a strict second-pass re-triage that specifically asked
  whether a defensible answer exists without the dev; it concluded yes. Not executed only because
  the session ended.
- Dropped via /cleanup-todos 2026-08-11: one-off request; the two-todo hand workaround already worked. Confirmed by dev 2026-08-11.
